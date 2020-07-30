#!/usr/bin/env python3

import os
import operator
import json
import logging

LOGGER_NAME = 'go'
LOGGER = logging.getLogger(LOGGER_NAME)


class Scoreboard:
    SCOREBOARD_FILE = 'scores.dat'

    def __init__(self, filename=SCOREBOARD_FILE):
        LOGGER.info('Loading scoreboard file "%s"', filename)
        self._filename = filename

        if not os.path.exists(filename):
            LOGGER.info('Scoreboard file is missing and will be created')
            with open(filename, 'x') as f:
                json.dump({}, f)

        with open(filename) as f:
            self._scores = self._check(json.load(f))

        LOGGER.info('Scoreboard was loaded')

    def _check(self, scores):
        LOGGER.info('Checking scoreboard data...')
        result = {}

        if not isinstance(scores, dict):
            LOGGER.error(
                'Invalid type of data: "%s". Scoreboard not loaded',
                type(scores))
            return result

        for (key, values) in scores.items():
            items = []
            if not isinstance(values, list):
                LOGGER.warning(
                    'Invalid type of entry\'s "%s" values: "%s". Skip',
                    key, type(values))
                continue

            for value in values:
                if not isinstance(value, list):
                    LOGGER.warning(
                        'Invalid type of scoreboard item in "%s": "%s". Skip',
                        key, type(value))
                    continue
                if len(value) != 2:
                    LOGGER.warning('Wrong scoreboard item: "%s". Skip', value)
                    continue
                if not isinstance(value[0], str):
                    LOGGER.warning(
                        'Invalid type of `name` in scoreboard item: '
                        '"%s". Skip', type(value[0]))
                    continue
                if not isinstance(value[1], int):
                    LOGGER.warning(
                        'Invalid type of `score` in scoreboard item: '
                        '"%s". Skip', type(value[1]))
                    continue
                if value[1] <= 0:
                    LOGGER.warning(
                        'Invalid value of `score` in scoreboard item: '
                        '"%s". Skip', value[1])
                    continue
                items.append(tuple(value))

            result[key] = items

        return result

    def add_score(self, size, name, score):
        name = str(name)
        score = int(score)
        key = str(size)

        LOGGER.info('Adding new record in "%s": <"%s", "%s">',
                    key, name, score)
        if key not in self._scores:
            self._scores[key] = []
        self._scores[key].append((name, score))

        with open(self._filename, 'w') as f:
            json.dump(self._scores, f)
        LOGGER.info('Record written')

    def get_scores(self, size):
        key = str(size)
        return sorted(self._scores.get(key, []),
                      key=operator.itemgetter(1), reverse=True)
