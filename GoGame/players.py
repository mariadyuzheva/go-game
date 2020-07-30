#!/usr/bin/env python3

import random
import multiprocessing.pool
import functools


def timeout():
    def timeout_decorator(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            pool = multiprocessing.pool.ThreadPool(processes=1)
            async_result = pool.apply_async(func, args, kwargs)
            max_timeout = args[2]
            result = async_result.get(max_timeout)
            return result
        return func_wrapper
    return timeout_decorator


class RealPlayer:
    """Реальный игрок"""
    def __init__(self, colour):
        """Создание нового игрока"""
        self._colour = colour

    def get_colour(self):
        return self._colour


class VirtualPlayer:
    def __init__(self, colour):
        self._colour = colour

    def get_colour(self):
        return self._colour

    def try_make_move(self, state, limit):
        return self.find_point_to_move(state, limit)

    def find_point_to_move(self, state, limit):
        return False, None, 0


class SimpleVirtualPlayer(VirtualPlayer):
    """Игрок, делающий ходы, не противоречащие правилам"""
    def __init__(self, colour):
        super().__init__(colour)

    def try_make_move(self, state, limit):
        """Ход игрока"""
        if self._colour == state.get_turn():
            if limit:
                limit *= 0.7

            try:
                return self.find_point_to_move(state, limit)

            except multiprocessing.TimeoutError:
                return False, None, 0

        return False, None, 0

    @timeout()
    def find_point_to_move(self, state, limit):
        free_points = list(state.get_free_points())
        random.shuffle(free_points)

        for point in free_points:
            try:
                return True, point, state.make_move(point)
            except ValueError:
                continue

        return False, None, 0


class CleverVirtualPlayer(VirtualPlayer):
    def __init__(self, colour):
        super().__init__(colour)

    def try_make_move(self, state, limit):
        if self._colour == state.get_turn():
            self._current_point = None

            if limit:
                limit *= 0.7

            try:
                return self.find_point_to_move(state, limit)

            except multiprocessing.TimeoutError:
                if self._current_point:
                    try:
                        return True, self._current_point, state.make_move(
                            self._current_point)
                    except ValueError:
                        return False, None, 0

        return False, None, 0

    @timeout()
    def find_point_to_move(self, state, limit):
        free_points = list(state.get_free_points())
        random.shuffle(free_points)
        moves = []
        forbidden_points = []

        for point in free_points:
            self._current_point = point

            if (point not in forbidden_points
                    and any(state.get_state(p) != self._colour
                            and self.check_liberties(state, point, p) == 0
                            for p in state.goban.neighbour_points(point))):
                try:
                    self._current_point = point
                    return True, point, state.make_move(point)

                except ValueError:
                    forbidden_points.append(point)
                    continue

        for point in free_points:
            if point not in forbidden_points:
                state.set_state(point, self._colour)

                if (state.count_liberties(point) == 1
                        and all(state.count_liberties(p) != 0
                                for p in
                                state.goban.neighbour_points(point))):
                    state.set_state(point, state.FREE)
                    forbidden_points.append(point)
                    continue

                state.set_state(point, state.FREE)

                if any(state.get_state(p) == self._colour
                       and state.count_liberties(p) == 1
                       for p in state.goban.neighbour_points(point)):
                    try:
                        self._current_point = point
                        return True, point, state.make_move(point)

                    except ValueError:
                        forbidden_points.append(point)
                        continue

                if any(state.get_state(p) != state.FREE
                       and state.get_state(p) != self._colour
                       for p in state.goban.neighbour_points(point)):
                    move = self.check_moves_to_take_stones(state, point)

                    if move:
                        moves.append((move, point))

        moves.sort(key=lambda x: x[0], reverse=True)

        while moves:
            min_move = moves.pop()
            try:
                self._current_point = min_move[1]
                return True, min_move[1], state.make_move(min_move[1])

            except ValueError:
                forbidden_points.append(min_move[1])
                state.set_state(min_move[1], state.FREE)
                continue

        for point in free_points:
            if (point not in forbidden_points
                    and any(state.get_state(p) != state.FREE
                            and state.get_state(p) != self._colour
                            for p in state.goban.neighbour_points(point))
                    and self.check_liberties(state, point, point) > 1):
                try:
                    self._current_point = point
                    return True, point, state.make_move(point)

                except ValueError:
                    forbidden_points.append(point)
                    continue

        for point in free_points:
            if point not in point not in forbidden_points:
                try:
                    self._current_point = point
                    return True, point, state.make_move(point)

                except ValueError:
                    forbidden_points.append(point)
                    continue

        return False, None, 0

    def check_moves_to_take_stones(self, state, point):
        next_points = [point]
        visited = []

        while next_points:
            current_point = next_points.pop()
            state.set_state(current_point, self._colour)
            visited.append(current_point)

            if any(state.count_liberties(p) == 0
                   for p in state.goban.neighbour_points(current_point)):
                self.free_visited(visited, state)
                return len(visited)

            for np in state.goban.get_next_points(current_point):
                if (state.get_state(np) == state.FREE
                        and (any(state.get_state(p) != state.FREE
                                 and state.get_state(p) != self._colour
                                 for p in state.goban.neighbour_points(np)))):
                    next_points.append(np)

        self.free_visited(visited, state)
        return 0

    def check_liberties(self, state, point, enemy_point):
        state.set_state(point, self._colour)
        liberties = state.count_liberties(enemy_point)
        state.set_state(point, state.FREE)
        return liberties

    @staticmethod
    def free_visited(visited, state):
        for v in visited:
            state.set_state(v, state.FREE)
