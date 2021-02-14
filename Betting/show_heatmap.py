from argparse import ArgumentParser, Namespace
from cli.cli import (add_database_option,
                     add_history_option,
                     add_league_option,
                     add_team_option,
                     add_half_option,
                     add_logging_options,
                     add_venue_option,
                     set_logging_options,
                     add_chunk_option,
                     get_unique_league)
from enum import auto, Enum
from lib.helpful import split_into_contiguous_groups, to_string
from lib.messages import error_message, warning_message
from matplotlib import pyplot as plt
from model.fixtures import Half, Event, win, defeat, draw, bts
from model.leagues import league_register, League
from model.seasons import Season
from model.tables import LeagueTable, TableMap
from seaborn import heatmap
from sql.sql import load_database
from typing import List

import numpy as np
import pandas as pd


class Analysis(Enum):
    RESULT = auto()
    SCORED = auto()
    GOALS = auto()

    @staticmethod
    def from_string(string: str):
        try:
            return Analysis[string.upper()]
        except KeyError:
            error_message("Analysis '{}' is not valid".format(string))


class Predicates:
    __slots__ = ['functions', 'mutual_exclusion']

    def __init__(self, functions, mutual_exclusion: bool):
        self.functions = functions
        self.mutual_exclusion = mutual_exclusion


predicate_table = {
    Analysis.RESULT: Predicates([win, draw, defeat],
                                False),

    Analysis.SCORED: Predicates([bts, Event.get('gf_gt_0'), Event.get('ga_gt_0'), Event.get('gfa_eq_0')],
                                True),

    Analysis.GOALS: Predicates([Event.get('gfa_gt_5'), Event.get('gfa_eq_5'), Event.get('gfa_eq_4'),
                                Event.get('gfa_eq_3'), Event.get('gfa_eq_2'), Event.get('gfa_eq_1'),
                                Event.get('gfa_eq_0')],
                               False)
}


def parse_command_line():
    parser = ArgumentParser(description='Show heatmap of data')
    add_database_option(parser)
    add_history_option(parser)
    add_league_option(parser)
    add_team_option(parser)
    add_half_option(parser)
    add_venue_option(parser)
    add_logging_options(parser)
    add_chunk_option(parser)

    parser.add_argument('-A',
                        '--analysis',
                        choices=Analysis,
                        type=Analysis.from_string,
                        metavar='{{{}}}'.format(','.join(analysis.name for analysis in Analysis)),
                        help='choose type of analysis',
                        required=True)

    return parser.parse_args()


def fill_matrix(matrix: np.ndarray, table_map: TableMap, table: LeagueTable, predicates: Predicates, half: Half):
    team_fixtures = table.season.fixtures_per_team()
    for position, row in enumerate(table):
        fixtures = team_fixtures[row.TEAM]
        results = []
        for fixture in fixtures:
            if half:
                if half == Half.first:
                    result = fixture.first_half()
                else:
                    result = fixture.second_half()
            else:
                result = fixture.full_time()

            if result:
                result = fixture.canonicalise_result(row.TEAM, result)
                results.append(result)
            else:
                warning_message('Ignoring {}'.format(fixture))

        totals = {func: 0 for func in predicates.functions}
        for result in results:
            satisfied = False
            for func in predicates.functions:
                if func(result):
                    totals[func] += 1
                    satisfied = True
                if predicates.mutual_exclusion and satisfied:
                    break

        for j, func in enumerate(predicates.functions):
            i = table_map.get_chunk(position)
            matrix[i, j] += totals[func]


def create_chunk_labels(table_map: TableMap):
    row_names = []
    for chunk_id in range(table_map.number_of_chunks()):
        chunk = table_map.get_rows(chunk_id)
        if chunk[0] == chunk[-1]:
            row_names.append('{}'.format(chunk[0] + 1))
        else:
            row_names.append('{}-{}'.format(chunk[0] + 1, chunk[-1] + 1))
    return row_names


def show(league: League, seasons: List[Season], datum: pd.DataFrame, analysis: Analysis, half: Half):
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(10, 10))
    heatmap(datum, cmap='coolwarm', linewidth=0.5, annot=True, fmt='d', ax=ax)
    ax.set_ylabel('Positions')
    ax.set_xlabel(analysis.name.capitalize())

    sublists = split_into_contiguous_groups([season.year for season in seasons])
    title = '{} {} Seasons:{}'.format(league.country, league.name, to_string(sublists))
    if half is not None:
        title = '{} ({} half)'.format(title, half.name)
    fig.suptitle(title, fontweight='bold', fontsize=14)

    plt.tight_layout()
    plt.show()


def main(args: Namespace):
    league = league_register[get_unique_league(args)]
    load_database(args.database, league)

    seasons = Season.seasons()
    if args.history:
        seasons = seasons[-args.history:]

    head_season = seasons[-1]
    head_table = LeagueTable(head_season)
    table_map = head_table.group(args.chunks)
    predicates = predicate_table[args.analysis]
    matrix = np.zeros(shape=(table_map.number_of_chunks(), len(predicates.functions)),
                      dtype=np.int32)

    for season in seasons:
        table = LeagueTable(season)
        table_map = table.group(args.chunks)
        fill_matrix(matrix, table_map, table, predicates, args.half)

    datum = pd.DataFrame(matrix)
    datum.columns = [Event.name(func, negate=False, short=True) for func in predicates.functions]
    datum.index = create_chunk_labels(table_map)

    show(league, seasons, datum, args.analysis, args.half)


if __name__ == '__main__':
    args = parse_command_line()
    set_logging_options(args)
    main(args)
