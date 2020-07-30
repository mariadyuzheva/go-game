#!/usr/bin/env python3
"""Модуль реализует логику игры «Го»"""

import collections
import itertools


class Goban:
    """Игровое поле"""
    def __init__(self, size):
        """Создание поля с заданным размером"""
        (is_correct, error) = Goban.check_size(size)
        if not is_correct:
            raise ValueError(error)

        self._size = cast_to_int(size)

    @staticmethod
    def check_size(size):
        """Проверка параметров поля"""
        size = cast_to_int(size)

        if len(size) != 2:
            return False, 'Wrong number of parameters'

        for (index, item) in enumerate(size):
            if item <= 0:
                return False, 'Parameter should be positive'

        return True, None

    def size(self):
        """Размеры поля"""
        return self._size

    def check_coordinates(self, point):
        """Проверка принадлежности координат полю"""
        if len(point) != len(self._size):
            return False

        return all(0 <= int(x) < self._size[i] for (i, x) in enumerate(point))

    def neighbour_points(self, point):
        """Соседние точки"""
        point = cast_to_int(point)

        if len(point) != len(self._size):
            raise ValueError('Wrong coordinates')

        for delta in (1, 0), (0, 1), (-1, 0), (0, -1):
            coords = tuple(map(sum, zip(point, delta)))
            if self.check_coordinates(coords):
                yield coords

    def get_next_points(self, point):
        point = cast_to_int(point)

        if len(point) != len(self._size):
            raise ValueError('Wrong coordinates')

        for delta in itertools.product((-1, 0, 1), (-1, 0, 1)):
            coords = tuple(map(sum, zip(point, delta)))
            if any(delta) and self.check_coordinates(coords):
                yield coords


class GameState:
    """Состояние игрового поля"""
    FREE = 0
    BLACK = 1
    GREY = 2
    WHITE = 3

    TURNS = [
        BLACK,
        GREY,
        WHITE
    ]

    def __init__(self, goban):
        """Создание начального состояния поля"""
        if not isinstance(goban, Goban):
            raise TypeError('Wrong type')

        self.goban = goban
        self._state = collections.defaultdict(lambda: self.FREE)

        for x in range(goban.size()[0]):
            for y in range(goban.size()[1]):
                self._state[(x, y)] = self.FREE

        self.dict_turns = {}
        self.get_turns_order()
        self._turn = self.BLACK

        self._score = {
            self.BLACK: 0,
            self.GREY: 0,
            self.WHITE: 0,
        }

    def set_state(self, point, value):
        self._state[point] = value

    def get_state(self, point):
        """Состояние точки поля"""
        return self._state[point]

    def get_full_state(self):
        return self._state

    def get_goban_size(self):
        return self.goban.size()[0]

    def get_turn(self):
        """Возвращает текущую очередь"""
        return self._turn

    def set_turn(self, colour):
        self._turn = colour

    def get_turns_order(self):
        for i in range(0, len(self.TURNS) - 1):
            self.dict_turns[self.TURNS[i]] = self.TURNS[i + 1]
        self.dict_turns[self.TURNS[len(self.TURNS) - 1]] = self.TURNS[0]

    def next_turn(self):
        """Передаёт очередь другому игроку"""
        self._turn = self.dict_turns[self._turn]

    def get_score(self):
        """Возвращает текущий счёт"""
        return self._score

    def set_score(self, colour, score):
        self._score[colour] = score

    def make_move(self, point):
        """Ход в указанную точку поля"""
        if not self.goban.check_coordinates(point):
            raise ValueError('Wrong coordinates of point')

        if self._state[point] == self.FREE:
            self._state[point] = self._turn

            self.check_for_suicide(point)
            taken_stones = self.take_stones(point)

            self.next_turn()
            return taken_stones
        else:
            raise ValueError('Player should move to a free point')

    def check_for_suicide(self, point):
        """Проверка на самоубийство"""
        if self.count_liberties(point) == 0:
            self._state[point] = self.FREE
            raise ValueError('This move leads to suicide')

    def take_stones(self, point):
        """Поиск групп для захвата и подсчёт очков"""
        taken_stones = 0
        for p in self.goban.neighbour_points(point):
            if (self._state[p] != self._turn
                    and self.count_liberties(p) == 0):
                score = self.catch_group(p)
                self.increase_score(score)
                taken_stones += score
        return taken_stones

    def take_territory(self, colour):
        visited = []
        score = 0

        for point in self.get_free_points():
            if point not in visited:
                group, boarder = self.get_group(point)

                for p in group:
                    visited.append(p)

                if all(self._state[p] == colour for p in boarder):
                    score += len(group)

        self._score[colour] += score

    def get_group(self, point):
        """Поиск камней, которые образуют группу"""
        point_state = self._state[point]
        group = {point}
        boarder = set()
        next_points = [point]

        while next_points:
            current_point = next_points.pop()
            group.add(current_point)

            for p in self.goban.neighbour_points(current_point):
                if self._state[p] == point_state and p not in group:
                    next_points.append(p)

                if self._state[p] != point_state:
                    boarder.add(p)

        return group, boarder

    def catch_group(self, point):
        """Захват группы камней противника"""
        group, boarder = self.get_group(point)
        score = len(group)

        for point in group:
            self._state[point] = self.FREE

        return score

    def increase_score(self, score):
        """Добавление очков"""
        self._score[self._turn] += score

    def get_liberties(self, point):
        """Поиск всех точек свободы"""
        point_state = self._state[point]
        next_points = [point]
        visited = []
        liberties = set()

        if point_state == self.FREE:
            return {point}

        else:
            while next_points:
                current_point = next_points.pop()
                visited.append(current_point)

                for p in self.goban.neighbour_points(current_point):
                    if self._state[p] == point_state and p not in visited:
                        next_points.append(p)
                    if self._state[p] == self.FREE:
                        liberties.add(p)

        return liberties

    def count_liberties(self, point):
        """Подсчёт количества точек свободы"""
        return len(self.get_liberties(point))

    def get_free_points(self):
        """Возвращает множество свободных точек поля"""
        return {point for point in self._state.keys()
                if self._state[point] == self.FREE}

    def get_winner(self):
        return [key for key in self._score.keys()
                if self._score[key] == max(self._score.values())]

    def convert_state_to_string(self):
        point_states = {
            GameState.BLACK: 'X',
            GameState.GREY: '#',
            GameState.WHITE: 'O',
            GameState.FREE: '.'
        }

        result = ''
        for y in range(self.goban.size()[1]):
            for x in range(self.goban.size()[0]):
                result += point_states[self._state[(x, y)]]
            result += ';'

        return result

    @staticmethod
    def convert_string_to_state(string, separator):
        point_states = {
            'X': GameState.BLACK,
            '#': GameState.GREY,
            'O': GameState.WHITE,
            '.': GameState.FREE
        }

        rows = list(filter(None, string.split(separator)))
        goban = Goban((len(rows[0]), len(rows)))
        state = GameState(goban)

        for x in range(len(rows[0])):
            for y in range(len(rows)):
                state.set_state((x, y), point_states[rows[y][x]])

        return state


def cast_to_int(iterable):
    """Переводит коллекцию в кортеж целых чисел"""
    return tuple(map(int, iterable))
