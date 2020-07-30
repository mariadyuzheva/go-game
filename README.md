# Игра «Го»
Версия 1.1

Автор: Дюжева Мария (mdyuzheva@gmail.com)


## Описание
Данное приложение является реализацией игры «Го» для трёх игроков 
с камнями трёх цветов: чёрными, серыми и белыми. В игре можно выбрать 
в качестве соперников реальных или виртуальных (простой и сложный уровень) игроков,
а также ввести ораничение времени на партию.


## Требования
* Python версии не ниже 3.6
* PyQt версии 5 с установленным QtWebKit для запуска графической версии


## Состав
* Графическая версия: `gograph.py`
* Модули: `GoGame/`
* Тесты: `tests/`


## Графическая версия
Справка по запуску: `./gograph.py --help`

Пример запуска: `./gograph.py`

### Управление

* ЛКМ — поставить камень в точку поля
* ПКМ - пропустить ход
* `Ctrl-N` — начать новую игру
* `Ctrl-O` — открыть сохранённую игру
* `Ctrl-S` — сохранить игру
* `Ctrl-R` — открыть таблицу рекордов


## Подробности реализации
Модули, отвечающие за логику игры, расположены в пакете GoGame.
В основе всего лежат класс `game.Goban`, реализующий хранение игрового поля,
класс `game.GameState`, реализующий хранение и изменение состояния игрового поля,
класс реального игрока `players.RealPlayer` и классы `players.VirtualPlayer` и 
`players.CleverVirtualPlayer`, реализующие простой и более сложный AI соответственно.

На модули `game` и `players` написаны тесты, их можно найти в `tests/`.
Покрытие тестами по строкам составляет около 92%

	GoGame\game.py           175      0   100%
	GoGame\players.py        148     26    82%   39, 42, 59-62, 72-73, 92-100, 120-122, 145-147, 180-182, 190-192

Приложение поддерживает отладочный режим, в логах можно видеть всю необходимую
информацию о работе приложения и возникающих ошибках.