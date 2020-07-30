#!/usr/bin/env python3
"""Графическая версия игры «Го»"""

ERROR_PYTHON_VERSION = 1
ERROR_MODULES_MISSING = 2
ERROR_QT_VERSION = 3

import sys

if sys.version_info < (3, 6):
    print('Use python >= 3.6', file=sys.stderr)
    sys.exit(ERROR_PYTHON_VERSION)

import argparse
from contextlib import contextmanager
import time
import logging
import json
import zlib

try:
    from GoGame import game, players, scoreboard
except Exception as e:
    print('Game modules not found: "{}"'.format(e), file=sys.stderr)
    sys.exit(ERROR_MODULES_MISSING)

try:
    from PyQt5 import QtWidgets, QtCore, QtGui
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except Exception as e:
    print('PyQt5 not found: "{}".'.format(e), file=sys.stderr)
    sys.exit(ERROR_QT_VERSION)


__version__ = '1.1'
__author__ = 'Dyuzheva Maria'
__email__ = 'mdyuzheva@gmail.com'

LOGGER_NAME = 'go'
LOGGER = logging.getLogger(LOGGER_NAME)


@contextmanager
def temp_painter(device):
    painter = QtGui.QPainter()
    painter.begin(device)
    try:
        yield painter
    finally:
        painter.end()


class GuiGoban(QtWidgets.QFrame):
    def __init__(self, window, size, log, start_time,
                 additional_time, parent=None):
        LOGGER.info('Creating new field with size %s:%s', size[0], size[1])
        super().__init__(parent)
        self._window = window
        self._parent = parent
        self._log = log
        self._start_time = start_time
        self._additional_time = additional_time
        self.is_saved = True

        self.w, self.h = convert_game_to_graph_coords(size)
        self.resize(self.w, self.h)
        self.goban = game.Goban(size)
        self.state = game.GameState(self.goban)

        self.pass_moves = {
            game.GameState.BLACK: 0,
            game.GameState.GREY: 0,
            game.GameState.WHITE: 0
        }

    def resize_goban(self):
        dx = self._window.width() - self._parent.width() + 50
        dy = self._window.height() - self._parent.height() + 30

        app = QtCore.QCoreApplication.instance()
        geom = app.desktop().availableGeometry()
        (max_w, max_h) = (geom.width(), geom.height())
        max_h -= app.style().pixelMetric(
            QtWidgets.QStyle.PM_TitleBarHeight)

        self._window.setMaximumSize(
            min(max_w, dx + self.width()),
            min(max_h, dy + self.height()))
        self._window.setFixedSize(self._window.maximumSize())

        self.repaint_goban()
        self.show()

    def repaint_goban(self):
        self.image = QtGui.QImage(
            self.w, self.h, QtGui.QImage.Format_ARGB32)
        self.image.fill(QtGui.QColor(253, 217, 181))

        with temp_painter(self.image) as painter:
            for i in range(30, self.w, 30):
                for j in range(30, self.h, 30):
                    pen = QtGui.QPen(QtCore.Qt.black)
                    painter.setPen(pen)
                    painter.drawLine(i, 30, i, self.h - 30)
                    painter.drawLine(30, j, self.w - 30, j)

            self.draw_coords(painter)

            for i in range(30, self.w, 30):
                for j in range(30, self.h, 30):
                    point = convert_graph_to_game_coords((i, j))

                    if self.state.get_state(point) != self.state.FREE:
                        stone = Stone((i, j), self.state.get_state(point))
                        stone.draw_stone(painter)
        self.repaint()

    def draw_coords(self, painter):
        font = QtGui.QFont('Monospace', 7, QtGui.QFont.Bold)
        painter.setFont(font)

        for width_index, x in enumerate(range(30, self.w, 30)):
            painter.drawText(x - 5, self.h, str(width_index))

        for height_index, y in enumerate(range(30, self.h, 30)):
            painter.drawText(0, y + 5, str(height_index))

    def mousePressEvent(self, event):
        turn = self.state.get_turn()

        if event.button() == QtCore.Qt.LeftButton:
            stone = Stone((event.x(), event.y()), turn)
            try:
                taken_stones = self.state.make_move(stone.game_point)
                self._log.add_move_info(turn, stone.game_point, taken_stones)
                self.pass_moves[turn] = 0
                self.is_saved = False

            except ValueError:
                QtWidgets.QMessageBox.critical(
                    self, 'Error', 'Wrong move!')
                return

        if event.button() == QtCore.Qt.RightButton:
            self._log.add_move_info(turn, None, 0)
            self.pass_moves[turn] += 1
            self.state.next_turn()

        if self._start_time:
            self._start_time[turn] += self._additional_time

    def paintEvent(self, event):
        with temp_painter(self) as painter:
            painter.drawImage(0, 0, self.image)


class HiScoresWindow(QtWidgets.QDialog):
    _TEMPLATE = """<html>
    <head>
        <style>
            table {{
                border: 3px double black;
                width: 100%;
            }}

            td.place {{ text-align: center; font-size: 17pt; }}
            td.name {{ font-size: 17pt; }}
            td.score {{ font-weight: bold; font-size: 17pt; }}
        </style>
    </head>
    <body>
        <h1 align='center'>{}</h1>
        <table>{}</table>
    </body>
</html>"""

    _ROW_TEMPLATE = """<tr>
<td class='place'>{}</td>
<td class='name'>{}</td>
<td class='score'>{}</td>
</tr>"""

    def __init__(self, scoreboard, size, parent=None):
        super().__init__(parent)
        self._size = size
        self._scores = scoreboard
        self._viewer = QWebEngineView()

        self._btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        self._btns.accepted.connect(self.close)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._viewer)
        layout.addWidget(self._btns)

        self.setLayout(layout)
        self.setWindowTitle('Go')

    @staticmethod
    def _make_row(place, name, score):
        return HiScoresWindow._ROW_TEMPLATE.format(place, name, score)

    def prepare(self):
        scores = self._scores.get_scores(self._size)

        table = ''.join(
            HiScoresWindow._make_row(place + 1, name, score)
            for (place, (name, score)) in enumerate(scores))

        self._viewer.setHtml(HiScoresWindow._TEMPLATE.format(
            'Records', table))


class GoGame(QtWidgets.QMainWindow):
    NAMES = {
        game.GameState.BLACK: 'Black',
        game.GameState.GREY: 'Grey',
        game.GameState.WHITE: 'White'
    }

    PLAYER_STATES = {
        players.RealPlayer: "Real player",
        players.SimpleVirtualPlayer: "Simple virtual player",
        players.CleverVirtualPlayer: "Clever virtual player",
        None: "Doesn't play"
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self._game_started = False
        self.show()
        self._set_params()

    def init_ui(self):
        self._new_game_dialog = StartGameWindow(self)
        self._new_game_dialog.setModal(True)
        self._new_game_dialog.accepted.connect(self._set_params)
        self._new_game_dialog.rejected.connect(self.close)

        self._size = self._new_game_dialog.set_size()

        self._scoreboard = None
        try:
            self._scoreboard = scoreboard.Scoreboard()
        except Exception as e:
            LOGGER.warning('Scoreboard error "%s"', e)
            print('\n'.join(('Scoreboard error', str(e))))
        else:
            LOGGER.info('Scoreboard OK')

        menu_bar = self.menuBar()
        goban_menu = menu_bar.addMenu('Game')

        self._new_game = QtWidgets.QAction('New game', self)
        self._new_game.setShortcut('Ctrl+N')
        goban_menu.addAction(self._new_game)
        self._new_game.triggered.connect(self._cmd_new_game)

        self._open_game = QtWidgets.QAction('Open', self)
        self._open_game.setShortcut('Ctrl+O')
        goban_menu.addAction(self._open_game)
        self._open_game.triggered.connect(self._cmd_open)

        self._save_game = QtWidgets.QAction('Save', self)
        self._save_game.setShortcut('Ctrl+S')
        goban_menu.addAction(self._save_game)
        self._save_game.triggered.connect(self._cmd_save)

        if self._scoreboard is not None:
            self._scores = QtWidgets.QAction('Records', self)
            self._scores.setShortcut('Ctrl+R')
            goban_menu.addAction(self._scores)
            self._scores.triggered.connect(self._cmd_scores)

        self.setWindowTitle('Go')

        self._scores_widget = QtWidgets.QWidget()
        self._scores_layout = QtWidgets.QVBoxLayout(self._scores_widget)
        self._scores_widget.setMinimumHeight(100)

        self._turn = QtWidgets.QLabel(self)
        self._turn.setFont(QtGui.QFont('Monospace', 10, QtGui.QFont.Bold))
        self._turn.setIndent(15)

        self._scroller = QtWidgets.QScrollArea(self)
        self._scroller.setFrameStyle(QtWidgets.QFrame.NoFrame)

        self._log = LogTable()
        self._start_time = {}
        self._additional_time = 0

        self._goban = GuiGoban(
            self, self._size, self._log, self._start_time,
            self._additional_time, self._scroller)
        self._scroller.setWidget(self._goban)

        first_layout = QtWidgets.QVBoxLayout()
        first_layout.addWidget(self._scores_widget, QtCore.Qt.AlignLeft)
        first_layout.addWidget(self._turn, QtCore.Qt.AlignLeft)
        first_layout.addWidget(self._scroller, QtCore.Qt.AlignJustify)

        second_layout = QtWidgets.QVBoxLayout()
        second_layout.addWidget(self._log)

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(first_layout)
        layout.addLayout(second_layout)

        window = QtWidgets.QWidget(self)
        window.setLayout(layout)
        self.resize(self._goban.w, self._goban.h + 130)
        self.setCentralWidget(window)

    def _set_params(self):
        players = self._new_game_dialog.set_players()
        size = self._new_game_dialog.set_size()
        game_time = self._new_game_dialog.set_time()
        self._additional_time = self._new_game_dialog.set_additional_time()

        if players and size:
            self._set_goban(size, players, game_time)
            LOGGER.info('Game started')
        else:
            self._new_game_dialog.open()

        if not self._game_started:
            self._start_game()

    def _set_goban(self, size, states, game_time):
        self._size = size
        self._start_time.clear()
        self._log.clear()

        self._goban = GuiGoban(
            self, self._size, self._log, self._start_time,
            self._additional_time, self._scroller)
        self._goban.resize_goban()
        self._scroller.setWidget(self._goban)

        self.players = {}
        self.active_players = []

        for turn, state in zip(self.NAMES.keys(), states):
            self.players[turn] = self._set_player_state(state, turn)
            if self.players[turn] is not None:
                self.active_players.append(turn)

        self._set_players()
        self._log.set_log_table(self.active_players)

        if game_time:
            self._set_time(game_time)
            self.timer.start()

    def delete_items(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                else:
                    self.delete_items(item.layout())

    def _set_players(self):
        self.delete_items(self._scores_layout)
        self._score = {}
        self._time_labels = {}

        for turn in self.active_players:
            player_layout = QtWidgets.QHBoxLayout()
            player = QtWidgets.QLabel(self)
            player.setFont(QtGui.QFont('Monospace', 10, QtGui.QFont.Bold))
            player.setText(f'{self.NAMES[turn]}:')

            self._score[turn] = QtWidgets.QLabel(self)
            self._score[turn].setFont(
                QtGui.QFont('Monospace', 10, QtGui.QFont.Bold))

            self._time_labels[turn] = QtWidgets.QLabel(
                time_to_str(0), self)
            self._time_labels[turn].setFont(
                QtGui.QFont('Monospace', 10, QtGui.QFont.Bold))

            player_layout.addWidget(player)
            player_layout.addWidget(self._score[turn])
            player_layout.addWidget(self._time_labels[turn])
            self._scores_layout.addLayout(player_layout)

        self._scores_widget.setFixedHeight(len(self.active_players) * 40)
        self._update_score()

    def _set_time(self, game_time):
        self.timer = QtCore.QTimer(self)

        for turn, time in zip(self.players.keys(), game_time):
            self._start_time[turn] = time

        for turn, time in zip(self.active_players, game_time):
            self._time_labels[turn].setText(time_to_str(time))
            LOGGER.info(
                f'Time for {self.NAMES[turn]} changed to {time / 60000} min')

        self.timer.setInterval(50)
        self.timer.timeout.connect(self.timerEvent)

    def timerEvent(self):
        turn = self._goban.state.get_turn()

        if self._start_time[turn] != 0:
            self._start_time[turn] -= 50

        for turn in self.active_players:
            self._time_labels[turn].setText(
                time_to_str(self._start_time[turn]))

    def _start_game(self):
        self._game_started = True
        while all(passed <= 1 for passed in self._goban.pass_moves.values()):
            self._player_move(self.players[self._goban.state.get_turn()])
            self._update_score()

            if (self._start_time
                    and all(v == 0 for v in self._start_time.values())):
                break

        if self._start_time:
            self.timer.stop()

        self._end_game()

    def _end_game(self):
        for player in self.players.keys():
            self._goban.state.take_territory(player)

        self._update_score()
        self._game_started = False
        self._goban.is_saved = True
        self._ask_for_new_game(self._get_game_result())

    def _get_game_result(self):
        winners = self._goban.state.get_winner()

        if len(winners) > 1:
            LOGGER.info('Game ended in a draw!')
            return 'Draw!'
        else:
            winner_colour = self.NAMES[winners[0]]
            LOGGER.info('Game over, %s win!', winner_colour)

            if (isinstance(self.players[winners[0]], players.RealPlayer)
                    and self._scoreboard is not None):
                name, ok = QtWidgets.QInputDialog.getText(
                    self, 'Game over!', '{} win!\nEnter your name:'.format(
                        winner_colour))
                if ok:
                    self._scoreboard.add_score(
                        self._size, name,
                        self._goban.state.get_score()[winners[0]])
                    return '{} wins!'.format(name)

            return '{} win!'.format(winner_colour)

    def _ask_for_new_game(self, result):
        answer = QtWidgets.QMessageBox.question(
            self, 'Game over!', '\n'.join(
                (result, 'Do you want to start new game?')),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if answer & QtWidgets.QMessageBox.Yes:
            self._set_params()

        if answer & QtWidgets.QMessageBox.No:
            self._goban.setDisabled(True)

    def _cmd_new_game(self):
        if self._start_time:
            self.timer.stop()

        if self._check_saved():
            self._new_game_dialog.open()

    def _cmd_scores(self):
        if self._start_time:
            self.timer.stop()

        self._scores_wnd = HiScoresWindow(self._scoreboard, self._size, self)
        self._scores_wnd.setModal(True)
        self._scores_wnd.prepare()
        self._scores_wnd.show()

    def _check_saved(self):
        if self._goban.is_saved:
            return True

        answer = QtWidgets.QMessageBox.question(
            self, 'Saving', 'Do you want to save the game?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            | QtWidgets.QMessageBox.Cancel)

        if answer & QtWidgets.QMessageBox.Cancel:
            return False

        if answer & QtWidgets.QMessageBox.Yes:
            self._cmd_save()

        return True

    def _cmd_open(self):
        if self._start_time:
            self.timer.stop()

        if not self._check_saved():
            return

        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open', 'saved')

        if filename:
            try:
                with open(filename, 'rb') as f:
                    self._load(f)
            except Exception as e:
                LOGGER.error(
                    'Failed to load game from "%s": "%s"', filename, e)
                QtWidgets.QMessageBox.critical(
                        self, 'Error', 'Load game error',
                        QtWidgets.QMessageBox.Ok)
            else:
                LOGGER.info('Loaded game from "%s"', filename)

    def _load(self, f):
        data = json.loads(zlib.decompress(f.read()).decode('utf-8'))

        for key in data:
            if key not in ('size', 'state', 'players', 'scores', 'turn',
                           'time', 'addition', 'log'):
                LOGGER.warning('Unknown field in file: "%s". Skip', key)

        for (name, ftype) in (('size', list), ('state', str),
                              ('players', list), ('scores', list),
                              ('turn', int), ('addition', float),
                              ('time', list), ('log', list)):
            if not isinstance(data[name], ftype):
                LOGGER.error(
                    'Invalid type of `%s` field: "%s"', name, type(data[name]))
                raise TypeError(name)

        LOGGER.info('Creating field')
        LOGGER.info('Setting players')
        LOGGER.info('Setting game time')
        LOGGER.info('Setting additional time')

        self._additional_time = data['addition']
        players = [StartGameWindow.PLAYER_STATES[player]
                   for player in data['players']]
        self._set_goban(data['size'], players, data['time'])

        LOGGER.info('Parsing state')
        loaded_state = game.GameState.convert_string_to_state(
            data['state'], ';')

        for x in range(data['size'][0]):
            for y in range(data['size'][1]):
                self._goban.state.set_state((x, y),
                                            loaded_state.get_state((x, y)))

        LOGGER.info('Setting scores')
        for name, score in zip(self.NAMES.keys(), data['scores']):
            self._goban.state.set_score(name, score)

        LOGGER.info('Setting turn')
        self._goban.state.set_turn(data['turn'])

        LOGGER.info('Setting log')
        self._log.fill_log_table(data['log'])

        self._goban.repaint_goban()

    def _cmd_save(self):
        if self._start_time:
            self.timer.stop()

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save', 'saved')
        if filename:
            try:
                with open(filename, 'wb') as f:
                    data = {
                        'size': self._size,
                        'state': self._goban.state.convert_state_to_string(),
                        'players': [self.PLAYER_STATES[type(player)]
                                    if player is not None
                                    else self.PLAYER_STATES[player]
                                    for player in self.players.values()],
                        'scores': [score for score in
                                   self._goban.state.get_score().values()],
                        'turn': self._goban.state.get_turn(),
                        'time': [start_time for start_time in
                                 self._start_time.values()],
                        'addition': self._additional_time,
                        'log': self._log.get_data_from_log_table()
                    }
                    f.write(
                        zlib.compress(json.dumps(data).encode('utf-8')))

            except Exception as e:
                LOGGER.error(
                    'Failed to save game to "%s": "%s"', filename, e)
                QtWidgets.QMessageBox.critical(
                        self, 'Error', 'Save game error',
                        QtWidgets.QMessageBox.Ok)

            else:
                self._goban.is_saved = True
                LOGGER.info('Saved game to "%s"', filename)

    def _update_score(self):
        for name, score in self._score.items():
            score.setText(str(self._goban.state.get_score()[name]))

    def _update_turn(self):
        self._turn.setText('Current move: {}'.format(
            self.NAMES[self._goban.state.get_turn()]))

    def closeEvent(self, event):
        if not self._check_saved():
            event.ignore()
        else:
            LOGGER.info('GUI Application closed')
            sys.exit()

    def _set_player_state(self, state, colour):
        LOGGER.info(
            f"State of {self.NAMES[colour]} player changed to "
            f"'{self.PLAYER_STATES[state]}'")

        if state is None:
            return None

        return state(colour)

    def _player_move(self, player):
        if isinstance(player, players.RealPlayer):
            turn = self._goban.state.get_turn()

            if self._start_time and self._start_time[turn] == 0:
                self.player_pass()
                return
            QtCore.QCoreApplication.processEvents()

        elif (isinstance(player, players.SimpleVirtualPlayer)
              or isinstance(player, players.CleverVirtualPlayer)):
            QtCore.QCoreApplication.processEvents(
                QtCore.QEventLoop.ExcludeUserInputEvents)
            self._virtual_player_move(player)

        else:
            self._goban.state.next_turn()

        self._update_turn()
        self._goban.repaint_goban()

    def _virtual_player_move(self, player):
        turn = self._goban.state.get_turn()

        if self._start_time:
            limit = self._start_time[turn] / 1000
            if limit == 0:
                self.player_pass()
                return
        else:
            limit = None

        ts = time.time()
        can_move, point, taken_stones = player.try_make_move(
            self._goban.state, limit)
        self._goban.state.set_turn(turn)

        if can_move:
            self._goban.pass_moves[turn] = 0
            while time.time() - ts < 1:
                QtCore.QCoreApplication.processEvents(
                    QtCore.QEventLoop.ExcludeUserInputEvents)

            self._log.add_move_info(turn, point, taken_stones)

            if self._start_time:
                self._start_time[turn] += self._additional_time

            if self._goban.state.get_turn() == turn:
                self._goban.state.next_turn()

            self._goban.is_saved = False
        else:
            self.player_pass()

    def player_pass(self):
        turn = self._goban.state.get_turn()
        self._log.add_move_info(turn, None, 0)
        self._goban.pass_moves[turn] += 1

        if self._start_time:
            self._start_time[turn] += self._additional_time

        self._goban.state.next_turn()


class LogTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(275)

        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

    def set_log_table(self, active_players):
        self._current_column = 0

        self.setColumnCount(len(active_players))
        self.setRowCount(1)
        self.setHorizontalHeaderLabels(
            [GoGame.NAMES[name] for name in active_players])

        column_count = self.columnCount()
        for column in range(column_count):
            self.setColumnWidth(column, 210 / column_count)

    def add_move_info(self, turn, point, taken_stones):
        if point is None:
            LOGGER.info(f'{GoGame.NAMES[turn]} pass')
            current_item = QtWidgets.QTableWidgetItem('pass')
        else:
            LOGGER.info(f'{GoGame.NAMES[turn]} make move {point}')
            current_item = QtWidgets.QTableWidgetItem(f'{point}')

        if taken_stones != 0:
            LOGGER.info(f'{GoGame.NAMES[turn]} take {taken_stones} stones')

        self.set_item(current_item)

    def get_data_from_log_table(self):
        data = []

        for row in range(self.rowCount()):
            for column in range(self.columnCount()):
                item = self.item(row, column)
                if item:
                    data.append(item.text())

        return data

    def fill_log_table(self, data):
        for item in data:
            self.set_item(QtWidgets.QTableWidgetItem(item))

    def set_item(self, item):
        self.setItem(self.rowCount() - 1, self._current_column, item)

        if self._current_column == self.columnCount() - 1:
            self.setRowCount(self.rowCount() + 1)
            self._current_column = 0
        else:
            self._current_column += 1


class Stone:
    COLOURS = {
        game.GameState.BLACK: QtGui.QColor(0, 0, 0),
        game.GameState.GREY: QtGui.QColor(192, 192, 192),
        game.GameState.WHITE: QtGui.QColor(255, 255, 255),
    }

    def __init__(self, coords, turn):
        self.graph_point = self.get_graph_point(coords)
        self.game_point = convert_graph_to_game_coords(self.graph_point)
        self.colour = self.COLOURS[turn]

    @staticmethod
    def get_graph_point(coords):
        delta_x = coords[0] % 30
        if delta_x >= 15:
            delta_x = delta_x - 30
        delta_y = coords[1] % 30
        if delta_y >= 15:
            delta_y = delta_y - 30
        return coords[0] - delta_x, coords[1] - delta_y

    def draw_stone(self, painter):
        painter.setPen(QtCore.Qt.black)
        painter.setBrush(self.colour)
        painter.drawEllipse(self.graph_point[0] - 15,
                            self.graph_point[1] - 15, 30, 30)


class StartGameWindow(QtWidgets.QDialog):
    """Окно выбора параметров игры"""
    PLAYER_STATES = {
        "Real player": players.RealPlayer,
        "Simple virtual player": players.SimpleVirtualPlayer,
        "Clever virtual player": players.CleverVirtualPlayer,
        "Doesn't play": None
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Go')

        self._set_size_layout()
        self._set_time_layout()
        self._set_additional_time_layout()

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addLayout(self.size_layout)
        top_layout.addLayout(self.time_layout)
        top_layout.addLayout(self.ad_time_layout)

        layout = QtWidgets.QVBoxLayout()

        params_title = QtWidgets.QLabel()
        params_title.setFont(QtGui.QFont('Monospace', 8, QtGui.QFont.Bold))
        params_title.setAlignment(QtCore.Qt.AlignHCenter)
        params_title.setText('Game parameters')

        layout.addWidget(params_title)
        layout.addLayout(top_layout)

        self._set_players_layout()

        players_title = QtWidgets.QLabel()
        players_title.setFont(QtGui.QFont('Monospace', 8, QtGui.QFont.Bold))
        players_title.setAlignment(QtCore.Qt.AlignHCenter)
        players_title.setText("Players' parameters")

        layout.addWidget(players_title)
        layout.addLayout(self.players_layout)

        self._buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout.addWidget(self._buttons)
        layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        self.setLayout(layout)

    def _set_size_layout(self):
        self._size_sel_layout = QtWidgets.QVBoxLayout()

        sizes = [
            '11:11',
            '15:15',
            '19:19'
        ]

        for s in sizes:
            self._size_sel_layout.addWidget(QtWidgets.QRadioButton(s))

        self._other = QtWidgets.QRadioButton('Other size')
        self._other.toggled.connect(self._click_other)
        self._size_sel_layout.addWidget(self._other)

        self._size_sel_layout.itemAt(0).widget().setChecked(True)

        self._selector = QtWidgets.QGroupBox()
        self._selector.setTitle('Field size')
        self._selector.setLayout(self._size_sel_layout)

        self._inputs = QtWidgets.QHBoxLayout()
        inp = QtWidgets.QLineEdit()
        self._inputs.addWidget(inp)
        self._inputs.itemAt(0).widget().setPlaceholderText('15:15')
        self._hide_inputs()

        self.size_layout = QtWidgets.QVBoxLayout()
        self.size_layout.addWidget(self._selector)
        self.size_layout.addLayout(self._inputs)

    def _click_other(self, show):
        self._hide_inputs(not show)
        if show:
            inp = self._inputs.itemAt(0).widget()
            inp.setFocus(QtCore.Qt.OtherFocusReason)

    def _hide_inputs(self, value=True):
        for idx in range(self._inputs.count()):
            self._inputs.itemAt(idx).widget().setVisible(not value)

        self.resize(self.width(), self.minimumSizeHint().height())

    def _set_time_layout(self):
        self._time_sel_layout = QtWidgets.QVBoxLayout()

        times = [
            'Without time limit',
            '1 minute',
            '3 minutes',
            '5 minutes',
        ]

        for t in times:
            self._time_sel_layout.addWidget(QtWidgets.QRadioButton(t))

        self._time_other = QtWidgets.QRadioButton('Other time (in minutes)')
        self._time_other.toggled.connect(self._click_time_other)
        self._time_sel_layout.addWidget(self._time_other)

        self._time_sel_layout.itemAt(0).widget().setChecked(True)

        self._time_selector = QtWidgets.QGroupBox()
        self._time_selector.setTitle('Game time')
        self._time_selector.setLayout(self._time_sel_layout)

        self._time_inputs = QtWidgets.QHBoxLayout()
        time_inp = QtWidgets.QLineEdit()
        self._time_inputs.addWidget(time_inp)
        self._time_inputs.itemAt(0).widget().setPlaceholderText('10')
        self._hide_time_inputs()

        self.time_layout = QtWidgets.QVBoxLayout()
        self.time_layout.addWidget(self._time_selector)
        self.time_layout.addLayout(self._time_inputs)

    def _click_time_other(self, show):
        self._hide_time_inputs(not show)
        if show:
            inp = self._time_inputs.itemAt(0).widget()
            inp.setFocus(QtCore.Qt.OtherFocusReason)

    def _hide_time_inputs(self, value=True):
        for idx in range(self._time_inputs.count()):
            self._time_inputs.itemAt(idx).widget().setVisible(not value)

        self.resize(self.width(), self.minimumSizeHint().height())

    def _set_additional_time_layout(self):
        self._ad_time_sel_layout = QtWidgets.QVBoxLayout()

        additions = [
            '0 seconds',
            '5 seconds',
            '10 seconds',
            '15 seconds',
        ]

        for ad in additions:
            self._ad_time_sel_layout.addWidget(QtWidgets.QRadioButton(ad))

        self._ad_time_other = QtWidgets.QRadioButton(
            'Other time (in seconds)')
        self._ad_time_other.toggled.connect(self._click_ad_time_other)
        self._ad_time_sel_layout.addWidget(self._ad_time_other)

        self._ad_time_sel_layout.itemAt(0).widget().setChecked(True)

        self._ad_time_selector = QtWidgets.QGroupBox()
        self._ad_time_selector.setTitle('Game additional time')
        self._ad_time_selector.setLayout(self._ad_time_sel_layout)

        self._ad_time_inputs = QtWidgets.QHBoxLayout()
        ad_time_inp = QtWidgets.QLineEdit()
        self._ad_time_inputs.addWidget(ad_time_inp)
        self._ad_time_inputs.itemAt(0).widget().setPlaceholderText('20')
        self._hide_ad_time_inputs()

        self.ad_time_layout = QtWidgets.QVBoxLayout()
        self.ad_time_layout.addWidget(self._ad_time_selector)
        self.ad_time_layout.addLayout(self._ad_time_inputs)

    def _click_ad_time_other(self, show):
        self._hide_ad_time_inputs(not show)
        if show:
            inp = self._ad_time_inputs.itemAt(0).widget()
            inp.setFocus(QtCore.Qt.OtherFocusReason)

    def _hide_ad_time_inputs(self, value=True):
        for idx in range(self._ad_time_inputs.count()):
            self._ad_time_inputs.itemAt(idx).widget().setVisible(not value)

    def _set_players_layout(self):
        self.players_layout = QtWidgets.QHBoxLayout()
        self._player_layouts = []

        players = [
            'First player (black)',
            'Second player (grey)',
            'Third player (white)'
        ]

        for player in players:
            self._sel_layout_new = QtWidgets.QVBoxLayout()

            for state in self.PLAYER_STATES.keys():
                self._sel_layout_new.addWidget(QtWidgets.QRadioButton(state))

            self._sel_layout_new.itemAt(0).widget().setChecked(True)
            self._player_layouts.append(self._sel_layout_new)

            self._selector_new = QtWidgets.QGroupBox()
            self._selector_new.setTitle(player)
            self._selector_new.setLayout(self._sel_layout_new)

            self.players_layout.addWidget(self._selector_new)

    def set_size(self):
        def convert(params):
            try:
                size = params.split(':', 1)
                if int(size[1]) >= 4 and int(size[0]) >= 4:
                    return int(size[0]), int(size[1])
                else:
                    QtWidgets.QMessageBox.critical(
                        self, 'Field size', 'Wrong field size!')

            except (IndexError, ValueError):
                QtWidgets.QMessageBox.critical(
                    self, 'Field size', 'Wrong format!')
            return 0

        if self._other.isChecked():
            return convert(self._inputs.itemAt(0).widget().text())

        for i in range(self._size_sel_layout.count() - 1):
            if self._size_sel_layout.itemAt(i).widget().isChecked():
                return convert(self._size_sel_layout.itemAt(i).widget().text())

    def set_time(self):
        def convert(game_time):
            try:
                if float(game_time) > 0:
                    start_time = float(game_time) * 60000
                    return [start_time, start_time, start_time]
                else:
                    QtWidgets.QMessageBox.critical(
                        self, 'Game time', 'Wrong time!')

            except ValueError:
                QtWidgets.QMessageBox.critical(
                    self, 'Game time', 'Wrong format!')
            return []

        if self._time_other.isChecked():
            return convert(self._time_inputs.itemAt(0).widget().text())

        if self._time_sel_layout.itemAt(0).widget().isChecked():
            return []

        for i in range(1, self._time_sel_layout.count() - 1):
            if self._time_sel_layout.itemAt(i).widget().isChecked():
                return convert(self._time_sel_layout.itemAt(i).widget().text().
                               split(' ')[0])

    def set_additional_time(self):
        def convert(additional_time):
            try:
                if float(additional_time) >= 0:
                    return float(additional_time) * 1000
                else:
                    QtWidgets.QMessageBox.critical(
                        self, 'Game time', 'Wrong time!')

            except ValueError:
                QtWidgets.QMessageBox.critical(
                    self, 'Game time', 'Wrong format!')
            return 0

        if self._ad_time_other.isChecked():
            return convert(self._ad_time_inputs.itemAt(0).widget().text())

        for i in range(0, self._ad_time_sel_layout.count() - 1):
            if self._ad_time_sel_layout.itemAt(i).widget().isChecked():
                return convert(
                    self._ad_time_sel_layout.itemAt(i).widget().text().
                    split(' ')[0])

    def set_players(self):
        chosen_players = []
        for layout in self._player_layouts:
            for i in range(layout.count()):
                if layout.itemAt(i).widget().isChecked():
                    chosen_players.append(
                        self.PLAYER_STATES[layout.itemAt(i).widget().text()])

        if players.RealPlayer not in chosen_players:
            QtWidgets.QMessageBox.critical(
                self, 'Players', 'At least one of the players should be real!')
            return []

        if chosen_players.count(None) > 1:
            QtWidgets.QMessageBox.critical(
                self, 'Players', 'At least two players should play!')
            return []

        return chosen_players


def convert_game_to_graph_coords(game_coords):
    return (game_coords[0] + 1) * 30, (game_coords[1] + 1) * 30


def convert_graph_to_game_coords(graph_coords):
    return int(graph_coords[0] / 30 - 1), int(graph_coords[1] / 30 - 1)


def time_to_str(time):
    return '{:.2f}'.format(time / 1000)


def parse_args():
    parser = argparse.ArgumentParser(
        usage='%(prog)s [OPTIONS]',
        description='Go game. GUI version {}'.format(__version__),
        epilog='Author: {} <{}>'.format(__author__, __email__))

    parser.add_argument(
        '-l', '--log', type=str,
        metavar='FILENAME', default='go.log', help='log filename')

    return parser.parse_args()


def main():
    args = parse_args()
    log = logging.FileHandler(args.log)
    log.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s <%(name)s>] %(message)s'))

    logger = logging.getLogger(sys.modules[__name__].LOGGER_NAME)
    logger.setLevel(logging.DEBUG if args.log else logging.ERROR)
    logger.addHandler(log)

    LOGGER.info('GUI Application started')

    app = QtWidgets.QApplication(sys.argv)
    GoGame()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
