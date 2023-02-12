#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import os
import re
import subprocess
import time
from datetime import timedelta
from pprint import pprint  # noqa

import coloredlogs
import humanize
from django.core.management.base import BaseCommand
from django.utils import timezone
from tabulate import tabulate

from .parse_statistic import Command as ParserCommand
from clist.models import Contest
from clist.templatetags.extras import get_problem_name, get_problem_short, has_season, md_escape, md_italic_escape
from ranking.models import Statistics
from tg.bot import Bot, telegram
from tg.models import Chat
from utils.attrdict import AttrDict

logger = logging.getLogger(__name__)
coloredlogs.install(logger=logger)


class Command(BaseCommand):
    help = 'Informer'

    def __init__(self, *args, **kw):
        super(Command, self).__init__(*args, **kw)

    def add_arguments(self, parser):
        parser.add_argument('--cid', type=int, help='Contest id', required=True)
        parser.add_argument('--tid', type=str, help='Telegram id for info', required=True)
        parser.add_argument('--delay', type=int, help='Delay between query in seconds', default=30)
        parser.add_argument('--query', help='Regex search query', default=None)
        parser.add_argument('--numbered', help='Regex numbering query', default=None)
        parser.add_argument('--top', type=int, help='Number top ignore query', default=None)
        parser.add_argument('--dryrun', action='store_true', help='Do not send to bot message', default=False)
        parser.add_argument('--dump', help='Dump and restore log file', default=None)

    def handle(self, *args, **options):
        self.stdout.write(str(options))
        args = AttrDict(options)
        logging.disable(logging.DEBUG)

        if not re.match(r'^-?\d+$', args.tid):
            tg_chat_id = Chat.objects.get(title=args.tid).chat_id
        else:
            tg_chat_id = args.tid

        bot = Bot()

        if args.dump is not None and os.path.exists(args.dump):
            with open(args.dump, 'r') as fo:
                standings = json.load(fo)
        else:
            standings = {}

        problems_info = standings.setdefault('__problems_info', {})

        parser_command = ParserCommand()

        iteration = 1 if args.dump else 0
        while True:
            subprocess.call('clear', shell=True)
            now = timezone.now()
            print(now)

            contest = Contest.objects.filter(pk=args.cid)
            parser_command.parse_statistic(contest, without_contest_filter=True)
            contest = contest.first()
            resource = contest.resource
            qs = Statistics.objects.filter(contest=contest)
            qs = qs.prefetch_related('account')
            statistics = list(qs)

            for p in problems_info.values():
                if p.get('accepted') or not p.get('n_hidden'):
                    p.pop('show_hidden', None)
                p['n_hidden'] = 0

            updated = False
            has_hidden = contest.has_hidden_results
            numbered = 0
            table_rows = []

            def statistics_sort_key(stat):
                return (
                    stat.place_as_int if stat.place_as_int is not None else float('inf'),
                    -stat.solving,
                )

            for stat in sorted(statistics, key=statistics_sort_key):
                name_instead_key = resource.info.get('standings', {}).get('name_instead_key')
                name_instead_key = stat.account.info.get('_name_instead_key', name_instead_key)

                if name_instead_key:
                    name = stat.account.name
                else:
                    name = stat.addition.get('name')
                    if not name or not has_season(stat.account.key, name):
                        name = stat.account.key

                filtered = False
                if args.query is not None and re.search(args.query, name, re.I):
                    filtered = True
                if args.top and stat.place_as_int and stat.place_as_int <= args.top:
                    filtered = True

                contest_problems = contest.info.get('problems')
                division = stat.addition.get('division')
                if division and 'division' in contest_problems:
                    contest_problems = contest_problems['division'][division]
                contest_problems = {get_problem_short(p): p for p in contest_problems}

                key = str(stat.account.id)
                standings_key = standings.get(key, {})
                problems = standings_key.get('problems', {})
                message_id = standings_key.get('messageId')

                def delete_message():
                    nonlocal message_id
                    if message_id:
                        for iteration in range(1, 5):
                            try:
                                bot.delete_message(chat_id=tg_chat_id, message_id=message_id)
                                message_id = None
                                break
                            except telegram.error.BadRequest as e:
                                logger.warning(str(e))
                                if 'Message to delete not found' in str(e):
                                    break
                                raise e
                            except telegram.error.TimedOut as e:
                                logger.warning(str(e))
                                time.sleep(iteration)
                                continue

                p = []
                has_update = False
                has_first_ac = False
                has_try_first_ac = False
                has_new_accepted = False
                has_top = False

                for k, v in stat.addition.get('problems', {}).items():
                    if 'result' not in v:
                        continue
                    p_info = problems_info.setdefault(k, {})
                    p_result = problems.get(k, {}).get('result')
                    result = v['result']

                    is_hidden = str(result).startswith('?')
                    is_accepted = str(result).startswith('+') or v.get('binary', False)
                    try:
                        is_accepted = is_accepted or float(result) > 0 and not v.get('partial')
                    except Exception:
                        pass

                    if is_hidden:
                        p_info['n_hidden'] = p_info.get('n_hidden', 0) + 1

                    if p_result != result or is_hidden:
                        has_new_accepted |= is_accepted
                        short = k
                        contest_problem = contest_problems.get(k, {})
                        if contest_problem and ('short' not in contest_problem or short != get_problem_short(contest_problem)):  # noqa
                            short = get_problem_name(contest_problems[k])
                            short = md_escape(short)
                        if 'url' in contest_problem:
                            short = '[%s](%s)' % (short, contest_problem['url'])

                        m = '%s%s %s' % (short, ('. ' + v['name']) if 'name' in v else '', result)

                        if v.get('verdict'):
                            m += ' ' + md_italic_escape(v['verdict'])

                        if p_result != result:
                            has_update = True
                            if iteration:
                                if p_info.get('show_hidden') == key:
                                    delete_message()
                                    if not is_hidden:
                                        p_info.pop('show_hidden')
                                if not p_info.get('accepted'):
                                    if is_accepted:
                                        m += ' FIRST ACCEPTED'
                                        has_first_ac = True
                                    elif is_hidden and not p_info.get('show_hidden'):
                                        p_info['show_hidden'] = key
                                        m += ' TRY FIRST AC'
                                        has_try_first_ac = True
                            if args.top and stat.place_as_int and stat.place_as_int <= args.top:
                                has_top = True
                        p.append(m)
                    if is_accepted:
                        p_info['accepted'] = True
                    has_hidden = has_hidden or is_hidden

                prev_place = standings_key.get('place')
                place = stat.place
                if has_new_accepted and prev_place:
                    place = '%s->%s' % (prev_place, place)
                if args.numbered is not None and re.search(args.numbered, stat.account.key, re.I):
                    numbered += 1
                    place = '%s (%s)' % (place, numbered)

                msg = ''
                if place is not None:
                    msg += '%s. ' % place
                msg += '_%s_' % md_italic_escape(name)
                if p:
                    msg = '%s, %s' % (', '.join(p), msg)
                if has_top:
                    msg += f' TOP{args.top}'

                if 'solving' not in standings_key or abs(standings_key['solving'] - stat.solving) > 1e-9:
                    msg += ' = %d' % stat.solving
                    if 'penalty' in stat.addition:
                        msg += f' ({stat.addition["penalty"]})'

                if has_update or has_first_ac or has_try_first_ac:
                    updated = True

                if filtered:
                    table_rows.append([stat.place, stat.solving, msg, stat.pk])
                if not args.dryrun and (filtered and has_update or has_first_ac or has_try_first_ac):
                    delete_message()
                    for iteration in range(1, 5):
                        try:
                            message = bot.send_message(msg=msg, chat_id=tg_chat_id)
                            message_id = message.message_id
                            break
                        except telegram.error.TimedOut as e:
                            logger.warning(str(e))
                            time.sleep(iteration * 3)
                            continue
                        except telegram.error.BadRequest as e:
                            logger.error(str(e))
                            break

                data = {
                    'solving': stat.solving,
                    'place': stat.place,
                    'problems': stat.addition.get('problems', {}),
                }
                if message_id is not None:
                    data['messageId'] = message_id
                standings[key] = data

            print(tabulate(table_rows, showindex=range(1, len(table_rows) + 1), tablefmt='rounded_outline'))

            if args.dump is not None and (updated or not os.path.exists(args.dump)):
                standings_dump = json.dumps(standings, indent=2)
                with open(args.dump, 'w') as fo:
                    fo.write(standings_dump)

            if iteration:
                is_over = contest.end_time < now
                if is_over and not has_hidden:
                    break
                is_coming = now < contest.start_time
                if is_coming:
                    limit = contest.start_time
                else:
                    tick = args.delay * 10 if is_over else args.delay
                    limit = now + timedelta(seconds=tick)
                size = 1
                prev_out = None
                print()
                while timezone.now() < limit:
                    value = humanize.naturaldelta(limit - timezone.now())
                    out = f'\r{value:{size}s} '
                    if out != prev_out:
                        size = len(value)
                        print(out, end='')
                        prev_out = out
                    time.sleep(1)
                print()

            iteration += 1
