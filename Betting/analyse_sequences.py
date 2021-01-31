from argparse import ArgumentParser, Namespace
from cli.cli import (add_database_option,
                     add_half_option,
                     add_history_option,
                     add_league_option,
                     add_team_option,
                     add_logging_options,
                     add_venue_option,
                     add_events_option,
                     get_multiple_teams,
                     set_logging_options)
from collections import Counter
from datetime import date, datetime, timedelta
from lib import messages
from model.fixtures import Half, Fixture, Result
from model.leagues import league_register
from model.seasons import Season
from model.teams import Team
from model.sequences import count_events, BarChart
from sql.sql import extract_picked_team, load_database, Database
from sql.sql_columns import ColumnNames
from sql.sql_language import Characters, Keywords
from typing import Callable


def parse_command_line():
    parser = ArgumentParser(description='Analyse sequence data and predict outcomes')
    add_database_option(parser)
    add_half_option(parser)
    add_history_option(parser)
    add_league_option(parser)
    add_team_option(parser)
    add_venue_option(parser)
    add_events_option(parser)
    add_logging_options(parser)

    parser.add_argument('--probability',
                        type=float,
                        help='only show events below or at this threshold',
                        default=0.1)

    parser.add_argument('-S',
                        '--show-match',
                        action='store_true',
                        help='show the next match even if it is beyond the next 24 hours',
                        default=False)

    parser.add_argument('--no-header',
                        action='store_true',
                        help='do not show the league header banner',
                        default=False)

    return parser.parse_args()


def probability(current_run: int, counter: Counter) -> float:
    if counter:
        numerator = 0
        for i in range(current_run + 1, len(counter) + 1):
            numerator += counter[i]
        return numerator / sum(counter.values())


def output_prediction(database_name: str,
                      season: Season,
                      team: Team,
                      half: Half,
                      aggregated_history: BarChart,
                      team_history: BarChart,
                      team_now: BarChart,
                      event_function: Callable,
                      threshold: float,
                      show_match: bool):
    aggregated_probability = probability(team_now.last, aggregated_history.counter)
    if aggregated_probability <= threshold:
        aggregated_message = 'Probability of extension is {:.3f} [aggregated]'.format(aggregated_probability)
    else:
        aggregated_message = None

    team_probability = probability(team_now.last, team_history.counter)
    if team_probability and team_probability <= threshold:
        team_message = 'Probability of extension is {:.3f}'.format(team_probability)
        team_message = '{} [based on {} individual observations]'.format(team_message,
                                                                         sum(team_history.counter.values()))
    else:
        team_message = None

    if aggregated_message is not None or team_message is not None:
        with Database(database_name) as db:
            season_constraint = "{}={}".format(ColumnNames.Season_ID.name, season.id)
            team_constraint = "({}={} {} {}={})".format(ColumnNames.Home_ID.name,
                                                        team.id,
                                                        Keywords.OR.name,
                                                        ColumnNames.Away_ID.name,
                                                        team.id)
            finished_constraint = "{}={}".format(ColumnNames.Finished.name, Characters.FALSE.value)
            constraints = [season_constraint, team_constraint, finished_constraint]
            fixture_rows = db.fetch_all_rows(Fixture.sql_table(), constraints)
            fixture_rows.sort(key=lambda row: row[1])
            fixture_rows = [row for row in fixture_rows if datetime.fromisoformat(row[1]).date() >= date.today()]
            if fixture_rows:
                row = fixture_rows[0]
                match_date = datetime.fromisoformat(row[1])
                match_date = match_date + timedelta(hours=1)
                window = datetime.now() + timedelta(hours=12)
                if match_date.date() <= window.date() or show_match:
                    home_team = Team.inventory[row[3]]
                    away_team = Team.inventory[row[4]]
                    header = '{} {} has {} the last {} {}'.format('>' * 10, team.name,
                                                                  Result.event_name(event_function).upper(),
                                                                  team_now.last,
                                                                  'games' if team_now.last > 1 else 'game')
                    if half:
                        header += ' ({} half)'.format(half.name)
                    next_match_message = 'Next match: {} {} vs. {}'.format(match_date.strftime('%Y-%m-%d %H.%M'),
                                                                           home_team.name,
                                                                           away_team.name)
                    remaining_matches_message = '{} matches remaining'.format(len(fixture_rows))
                    message = '{}\n{}{}{}\n{}\n'.format(header,
                                                        aggregated_message + '\n' if aggregated_message else '',
                                                        team_message + '\n' if team_message else '',
                                                        next_match_message,
                                                        remaining_matches_message)
                    print(message)


def main(arguments: Namespace):
    for league_code in arguments.league:
        league = league_register[league_code]
        load_database(arguments.database, league)

        seasons = Season.seasons()
        if not seasons:
            messages.error_message("No season data found")

        if arguments.history:
            seasons = seasons[-arguments.history:]

        if seasons[-1].current:
            this_season = seasons.pop()

            if arguments.team:
                teams = []
                for team_name in get_multiple_teams(arguments):
                    team = extract_picked_team(arguments.database, team_name, league)
                    teams.append(team)
            else:
                teams = this_season.teams()

            if arguments.event:
                events = [getattr(Result, event) for event in arguments.event]
            else:
                events = [Result.not_drawn, Result.not_lost, Result.not_won]

            histories = {}
            for event in events:
                histories[event] = BarChart(Counter(), [seasons[0].year, seasons[-1].year])
                for season in seasons:
                    for team in season.teams():
                        count_events(season, team, arguments.venue, arguments.half, event, histories[event])

            if not arguments.no_header:
                messages.vanilla_message("{} Analysing sequences for {} {} {}".format('*' * 80 + '\n',
                                                                                      league.country,
                                                                                      league.name,
                                                                                      '\n' + '*' * 80))

            for team in teams:
                for event in events:
                    team_history = BarChart(Counter(), [seasons[0].year, seasons[-1].year])
                    for season in seasons:
                        count_events(season, team, arguments.venue, arguments.half, event, team_history)

                    team_now = BarChart(Counter(), [this_season.year], team)
                    count_events(this_season, team, arguments.venue, arguments.half, event, team_now)

                    if team_now.last:
                        output_prediction(arguments.database,
                                          this_season,
                                          team,
                                          arguments.half,
                                          histories[event],
                                          team_history,
                                          team_now,
                                          event,
                                          arguments.probability,
                                          arguments.show_match)
        else:
            messages.error_message("The current season has not yet started")


if __name__ == '__main__':
    arguments = parse_command_line()
    set_logging_options(arguments)
    main(arguments)
