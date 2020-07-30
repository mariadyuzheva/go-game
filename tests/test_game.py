#!/usr/bin/env python3

import os
import sys
import unittest
import multiprocessing

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             os.path.pardir))
from GoGame.game import Goban, GameState
from GoGame.players import RealPlayer, SimpleVirtualPlayer, CleverVirtualPlayer


class GobanTest(unittest.TestCase):
    def test_init_goban(self):
        goban = Goban((3, 3))

        self.assertTupleEqual((3, 3), goban.size())

    def test_init_errors(self):
        for (width, height) in (([], 1), (1, []), ([], [])):
            with self.assertRaises(TypeError):
                Goban((width, height))

        for (width, height) in ((0, 0), (-10, -10), (10, -10)):
            with self.assertRaises(ValueError):
                Goban((width, height))

        with self.assertRaises(ValueError):
            Goban((2, 2, 2))

    def test_check_size(self):
        self.assertFalse(Goban.check_size((-19, -19))[0])
        self.assertFalse(Goban.check_size((3, 3, 3))[0])
        self.assertFalse(Goban.check_size((10,))[0])
        self.assertTrue(Goban.check_size((10, 10))[0])
        self.assertTrue(Goban.check_size((10, 12))[0])

    def test_coordinates_check(self):
        goban = Goban((10, 10))

        self.assertFalse(goban.check_coordinates((1, 0, 1)))

        for point in ((5, 5), (0, 0), (0, 6), (9, 0), (9, 6), (9, 9)):
            self.assertTrue(goban.check_coordinates(point))

        for point in ((-1, 4), (1, -4), (-1, -4), (10, 4), (1, 10), (10, 10)):
            self.assertFalse(goban.check_coordinates(point))

    def test_neighbour_points(self):
        goban = Goban((4, 4))

        with self.assertRaises(ValueError):
            set(goban.neighbour_points((1, 1, 1)))

        for (point, neighbours) in (((0, 0), {(0, 1), (1, 0)}),
                                    ((0, 1), {(0, 0), (0, 2), (1, 1)}),
                                    ((1, 1), {(0, 1), (1, 0), (1, 2),
                                              (2, 1)})):
            self.assertSetEqual(neighbours, set(goban.neighbour_points(point)))

    def test_get_next_points(self):
        goban = Goban((3, 3))

        with self.assertRaises(ValueError):
            set(goban.get_next_points((1, 1, 1)))

        for (point, neighbours) in (((0, 0), {(0, 1), (1, 0), (1, 1)}),
                                    ((0, 1), {(0, 0), (0, 2), (1, 1), (1, 0),
                                              (1, 2)}),
                                    ((1, 1), {(0, 0), (0, 1), (1, 0), (1, 2),
                                              (2, 1), (2, 2), (2, 0),
                                              (0, 2)})):
            self.assertSetEqual(neighbours, set(goban.get_next_points(point)))


class GameStateTest(unittest.TestCase):
    def test_init_state(self):
        goban = Goban((2, 2))
        state = GameState(goban)

        for point in ((0, 0), (1, 0), (0, 1), (1, 1)):
            self.assertEqual(GameState.FREE, state._state[point])

    def test_init_error(self):
        with self.assertRaises(TypeError):
            GameState([])

    def test_get_state(self):
        goban = Goban((2, 2))
        state = GameState(goban)

        self.assertEqual(state.get_state((1, 1)), GameState.FREE)

        state._state[(1, 1)] = GameState.WHITE
        self.assertEqual(state.get_state((1, 1)), GameState.WHITE)

    def test_get_full_state(self):
        goban = Goban((2, 2))
        state = GameState(goban)
        state.set_state((1, 1), GameState.WHITE)

        self.assertDictEqual(state.get_full_state(), state._state)

    def test_get_goban_size(self):
        goban = Goban((3, 3))
        state = GameState(goban)

        self.assertEqual(state.get_goban_size(), 3)

    def test_get_turn(self):
        goban = Goban((2, 2))
        state = GameState(goban)

        self.assertEqual(state._turn, GameState.BLACK)
        state.next_turn()
        self.assertEqual(state._turn, GameState.GREY)
        state.next_turn()
        self.assertEqual(state._turn, GameState.WHITE)
        state.next_turn()
        self.assertEqual(state._turn, GameState.BLACK)

    def test_set_turn(self):
        goban = Goban((2, 2))
        state = GameState(goban)
        state.set_turn(GameState.WHITE)

        self.assertEqual(state.get_turn(), GameState.WHITE)

    def test_score(self):
        goban = Goban((2, 2))
        state = GameState(goban)

        self.assertEqual(state._score, {1: 0, 2: 0, 3: 0})

        state.increase_score(2)
        state.next_turn()
        state.increase_score(3)
        state.next_turn()
        state.increase_score(4)

        self.assertEqual(state._score, {1: 2, 2: 3, 3: 4})

    def test_set_score(self):
        goban = Goban((2, 2))
        state = GameState(goban)
        state.set_score(GameState.WHITE, 5)
        state.set_score(GameState.BLACK, 2)

        self.assertEqual(state.get_score(), {1: 2, 2: 0, 3: 5})

    def test_move(self):
        goban = Goban((2, 2))
        state = GameState(goban)

        state.make_move((1, 1))
        self.assertEqual(state.get_state((1, 1)), GameState.BLACK)
        self.assertEqual(state._turn, GameState.GREY)

        for point in ((2, 3), (1, 1)):
            with self.assertRaises(ValueError):
                state.make_move(point)

    def test_suicide(self):
        string = '''
        XXX..
        XOX..
        XXX..
        .....
        .....
        '''
        state = GameState.convert_string_to_state(string, '\n        ')

        with self.assertRaises(ValueError):
            state.check_for_suicide((1, 1))

    def test_count_liberties(self):
        string = '''
        X....
        .....
        .....
        .....
        .....
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        self.assertEqual(state.count_liberties((0, 0)), 2)

        string = '''
        X....
        .X...
        .....
        .....
        .....
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        self.assertEqual(state.count_liberties((1, 1)), 4)

        string = '''
        X....
        XX...
        .....
        .....
        .....
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        self.assertEqual(state.count_liberties((0, 0)), 4)

    def test_take_stones(self):
        string = '''
        OX...
        OX...
        X....
        .....
        '''
        state = GameState.convert_string_to_state(string, '\n        ')

        self.assertEqual(state.take_stones((0, 0)), 2)

    def test_take_territory(self):
        string = '''
        .X...
        .X...
        X...O
        ...O.
        ....O
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        state.take_territory(GameState.BLACK)
        state.take_territory(GameState.WHITE)

        self.assertEqual(state._score[GameState.BLACK], 2)
        self.assertEqual(state._score[GameState.WHITE], 1)

    def test_get_group(self):
        string = '''
        XX...
        XX...
        .....
        .....
        .....
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        group, boarder = state.get_group((0, 0))

        self.assertEqual(group, {(0, 0), (0, 1), (1, 0), (1, 1)})
        self.assertEqual(boarder, {(0, 2), (1, 2), (2, 0), (2, 1)})

        string = '''
        XX...
        XO...
        .....
        .....
        .....
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        group, boarder = state.get_group((0, 0))

        self.assertEqual(group, {(0, 0), (0, 1), (1, 0)})
        self.assertEqual(boarder, {(0, 2), (1, 1), (2, 0)})

    def test_catch_group(self):
        goban = Goban((5, 5))
        state = GameState(goban)

        state._state[(1, 1)] = GameState.BLACK
        self.assertEqual(state.catch_group((1, 1)), 1)
        self.assertEqual(state.get_state((1, 1)), GameState.FREE)

        string = '''
        XXX..
        XXX..
        .....
        .....
        .....
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        self.assertEqual(state.catch_group((1, 1)), 6)

        for x in range(0, 3):
            for y in range(0, 2):
                self.assertEqual(state.get_state((x, y)), GameState.FREE)

    def test_get_free_points(self):
        goban = Goban((2, 2))
        state = GameState(goban)

        self.assertSetEqual(state.get_free_points(),
                            {(0, 0), (0, 1), (1, 0), (1, 1)})
        state._state[(0, 0)] = GameState.BLACK
        self.assertSetEqual(state.get_free_points(),
                            {(0, 1), (1, 0), (1, 1)})

    def test_get_winner(self):
        goban = Goban((2, 2))
        state = GameState(goban)
        state._score = {
            GameState.BLACK: 0,
            GameState.GREY: 0,
            GameState.WHITE: 0
        }
        self.assertEqual(state.get_winner(), [GameState.BLACK,
                                              GameState.GREY,
                                              GameState.WHITE])

        state._score = {
            GameState.BLACK: 0,
            GameState.GREY: 1,
            GameState.WHITE: 1
        }
        self.assertEqual(state.get_winner(), [GameState.GREY,
                                              GameState.WHITE])

        state._score = {
            GameState.BLACK: 0,
            GameState.GREY: 1,
            GameState.WHITE: 2
        }
        self.assertEqual(state.get_winner(), [GameState.WHITE])

    def test_convert_state_to_string(self):
        goban = Goban((2, 2))
        state = GameState(goban)

        state._state[(0, 0)] = GameState.BLACK
        state._state[(1, 0)] = GameState.GREY
        state._state[(0, 1)] = GameState.WHITE

        self.assertEqual(state.convert_state_to_string(), 'X#;O.;')

    def test_convert_string_to_state(self):
        goban = Goban((2, 2))
        state = GameState(goban)

        state._state[(0, 0)] = GameState.BLACK
        state._state[(1, 0)] = GameState.GREY
        state._state[(0, 1)] = GameState.WHITE

        first_string = '''
        X#
        O.
        '''
        first_state = state.convert_string_to_state(first_string, '\n        ')

        second_string = 'X#;O.;'
        second_state = state.convert_string_to_state(second_string, ';')

        self.assertDictEqual(first_state._state, state._state)
        self.assertDictEqual(second_state._state, state._state)


class RealPlayerTest(unittest.TestCase):
    def test_init_player(self):
        goban = Goban((2, 2))
        state = GameState(goban)
        player = RealPlayer(state.BLACK)

        self.assertEqual(player.get_colour(), state.BLACK)


class VirtualPlayerTest(unittest.TestCase):
    def test_init_player(self):
        goban = Goban((2, 2))
        state = GameState(goban)
        player = SimpleVirtualPlayer(state.GREY)

        self.assertEqual(player.get_colour(), state.GREY)

    def test_try_make_move(self):
        goban = Goban((2, 2))
        state = GameState(goban)
        player = SimpleVirtualPlayer(state.GREY)

        state._turn = state.GREY
        move = player.try_make_move(state, 60)
        self.assertEqual(move[0], True)
        self.assertTrue(move[1] in [(0, 0), (1, 0), (0, 1), (1, 1)])

        state._turn = state.GREY
        state._state[(0, 0)] = GameState.BLACK
        move = player.try_make_move(state, 60)
        self.assertEqual(move[0], True)
        self.assertTrue(move[1] in [(0, 1), (1, 0), (1, 1)])

        string = '''
        XX
        XX
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        state._turn = state.GREY

        self.assertEqual(player.try_make_move(state, 60), (False, None, 0))


class CleverVirtualPlayerTest(unittest.TestCase):
    def test_init_player(self):
        goban = Goban((2, 2))
        state = GameState(goban)
        player = CleverVirtualPlayer(state.GREY)

        self.assertEqual(player.get_colour(), state.GREY)

    def test_try_make_move(self):
        goban = Goban((3, 3))
        state = GameState(goban)
        player = CleverVirtualPlayer(state.GREY)

        state._turn = state.GREY
        points = state.get_free_points()
        move = player.try_make_move(state, 60)
        self.assertEqual(move[0], True)
        self.assertTrue(move[1] in points)

        string = '''
        ..X
        ...
        ...
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        state._turn = state.GREY
        move = player.try_make_move(state, 60)

        self.assertEqual(move[0], True)
        self.assertTrue(move[1] in [(1, 0), (2, 1)])

        string = '''
        .X.
        O.X
        .O.
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        state._turn = state.GREY

        self.assertEqual(player.try_make_move(state, 60), (False, None, 0))

    def test_move_if_one_liberty(self):
        string = '''
        XO
        X.
        ..
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        player = CleverVirtualPlayer(state.WHITE)
        state._turn = state.WHITE

        self.assertEqual(player.try_make_move(state, 60), (True, (1, 2), 0))

        string = '''
        .XO
        ...
        ...
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        player = CleverVirtualPlayer(state.WHITE)
        state._turn = state.WHITE

        self.assertEqual(player.try_make_move(state, 60), (True, (2, 1), 0))

        string = '''
        ....
        O#..
        .O#.
        .#..
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        player = CleverVirtualPlayer(state.GREY)
        state._turn = state.GREY

        self.assertEqual(player.try_make_move(state, 60), (True, (0, 2), 1))

    def test_random_move(self):
        string = '''
        ....
        .#X.
        ..X#
        ....
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        player = CleverVirtualPlayer(state.GREY)
        state._turn = state.GREY

        move = player.try_make_move(state, 60)[1]
        self.assertTrue(move in [(2, 0), (3, 1), (2, 3), (1, 2)])

    def test_check_moves_to_take_stones(self):
        string = '''
        ..X
        ...
        ...
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        player = CleverVirtualPlayer(state.GREY)
        self.assertEqual(player.check_moves_to_take_stones(state, (1, 0)), 2)

        string = '''
        .O.
        #X.
        .O.
        '''
        state = GameState.convert_string_to_state(string, '\n        ')
        self.assertEqual(player.check_moves_to_take_stones(state, (2, 1)), 1)

        state = GameState.convert_string_to_state(string, '\n        ')
        self.assertEqual(player.check_moves_to_take_stones(state, (2, 0)), 2)

    def test_find_point_with_lack_of_time(self):
        goban = Goban((100, 100))
        state = GameState(goban)
        player = CleverVirtualPlayer(state.BLACK)

        with self.assertRaises(multiprocessing.TimeoutError):
            player.find_point_to_move(state, 0.01)


if __name__ == '__main__':
    unittest.main()
