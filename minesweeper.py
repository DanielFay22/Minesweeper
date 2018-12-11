"""
Program for playing the game Minesweeper!

Created by Daniel Fay
"""


from tkinter import *
from PIL import Image, ImageTk
from random import randint
from copy import deepcopy
import numpy as np
from collections import deque

# Declare global variables
WIDTH = 16
HEIGHT = 30
MINES = 99
difficulty = "expert"

mode = 0
elapsed = 0
flags = 0
photos = {}

# Files is the list of names of image files to load. To add a new image, add the file name to files and 
# the image will be loaded as an image object and mapped to the filename in photos
files = ['1','2','3','4','5','6','7','8','blank','flag','mine','mine2','question','tile','mine_image']

gameover = False
restart_time = False
paused = False
cheating = True
cheatstring = 'aaaaaa'

class Tile:
    """
    A single tile in a minesweeper board.
    """
    def __init__(self, pos):
        """
        Initialize a tile as a button at the specified grid location.
        """
        self._button = None

        self.is_mine = False
        self.flipped = False
        self._isflag = False
        self._isquestion = False

        self._mines = 0
        self._image = 'tile'
        self._pos = pos

    def make_widget(self):
        """
        Draw the tile at its set position on root.
        """
        # Draw the tile and set handlers for clicks.
        self._button = Label(master=board, image=photos[self._image], relief=GROOVE)
        self._button.bind("<Button-1>", self.click)
        self._button.bind("<Button-3>", self._right_click)
        self._button.grid(row=self._pos[0],column=self._pos[1])
    
    def set_flag(self, flag):
        """
        Add/remove flag and update tile image.
        """
        global flags
        # Update flag count
        flags -= int(self._isflag) - int(flag)

        self._isflag = flag
        self._isquestion = False

        # Update tile image and mine counter
        if flag:
            self._image = 'flag'
        else:
            self._image = 'tile'
        self._update_img()
        update_flags()

        return

    def _right_click(self, event):
        """
        Event handler for right click on a tile.

        Right click toggles tile in the following order: tile-flag-question-tile...
        """
        global gameover, paused
        if gameover or paused:
            return

        if not self.flipped:
            if self._isflag:
                self.set_question(True)

            elif self._isquestion:
                self.set_question(False)

            else:
                self.set_flag(True)

        return

    def set_question(self, quest):
        """
        Add/remove a question mark from the tile and update the tile image.
        """
        global flags
        self._isquestion = quest

        if self._isflag:
            flags -= 1
            self._isflag = False

        # Update tile image and mine counter
        if self._isquestion:
            self._image = 'question'
        else:
            self._image = 'tile'
        self._update_img()
        update_flags()
        return

    def _update_img(self):
        """
        Redraw the image for the tile.
        """
        self._button.config(image=photos[self._image])

    def click(self, event=None):
        # Stub handler for widget
        pass

    def is_flag(self):
        """
        Return whether a flag is flagged.
        """
        return self._isflag

    def change_cursor(self, strg):
        """
        Set the button for the tile to have the given cursor option.
        """
        self._button.config(cursor=strg)
        return

    def get_pos(self):
        """
        Return the position of the tile.
        """
        return tuple(self._pos)

    def get_mines_near(self):
        """
        Returns the number of mines adjacent to the tile.
        """
        return self._mines
    
    
class Mine(Tile):
    def __init__(self, pos):
        super(Mine, self).__init__(pos)
        self.is_mine = True

        self.make_widget()

    def flip(self) -> list:
        self._image = 'mine'
        self._button.config(image=photos[self._image], command=None)
        return []

    def click(self, event=None):
        if gameover or paused or self.flipped:
            return
        if not mode:
            if not self._isflag:
                self._button.config(image=photos["mine2"], command=None)
                self.flipped = True
                lose()
        elif mode == 1:
            self.set_flag(not self._isflag)
        elif mode == 2:
            self.set_question(not self._isquestion)

class Number(Tile):
    def __init__(self, pos, num):
        super(Number, self).__init__(pos)
        self._mines = num

        self.make_widget()

    def flip(self) -> list:
        if not self.flipped: flipped = [self]
        else: flipped = []
        self.flipped = True

        self._image = str(self._mines) if self._mines else 'blank'
        self._button.config(image=photos[self._image], command=None)

        if not self._mines:
            flipped.extend(clear_adjacent(self._pos))

        return flipped

    def click(self, event=None):
        if gameover or paused or self.flipped:
            return

        if not mode:
            if not self._isflag:
                self.flip()
        elif mode == 1:
            self.set_flag(not self._isflag)
        elif mode == 2:
            self.set_question(not self._isquestion)


def create_board(height, width, mines):
    """
    Create a board with the given height, width, and number of mines.
    For each non-mine tile set the number of mines nearby.
    """
    board = np.arange(height * width)
    np.random.shuffle(board)
    board = board.reshape((width, -1))
    board[board >= height * width - mines] = -1

    res = board.copy().astype('object')

    dirs = [(1, 1), (1, 0), (1, -1), (0, 1), (0, -1), (-1, 1), (-1, 0), (-1, -1)]
    for i, j in [(x, y) for x in range(width) for y in range(height)]:
        if board[i, j] == -1:
            res[i, j] = Mine((i, j))
        else:
            coords = filter(lambda x: 0 <= x[0] < width and 0 <= x[1] < height,
                            map(lambda x: tuple(np.add((i, j), x)), dirs))
            # print(sum(map(lambda x: int(board[x] == -1), coords)))
            res[i, j] = Number( (i, j), sum(map(lambda x: int(board[x] == -1), coords)))

    return res

def get_neighbors(board, pos):
    """
    Return the number of neighboring tiles which are mines.
    """
    return sum(map(lambda x: x.is_mine, neighbors(board[pos], board)))

def is_valid(row, col):
    """
    Returns whether there is a tile at the given coordinates.
    """
    global WIDTH, HEIGHT
    if 0 <= row < HEIGHT and 0 <= col < WIDTH:
        return True
    return False

def clear_adjacent(pos):
    """
    Clears all neighboring empty tiles (tiles with 0 adjacent mines)
    Flips each tile adjacent to itself, each of these tiles which is empty calls clear_adjacent again.
    """
    flipped = []
    nbrs = neighbors(gameboard[pos], gameboard)
    for nbr in filter(lambda x: not x.flipped, nbrs):
        flipped.extend(nbr.flip())
    return flipped

def toggle_mode(event=0):
    """
    On button click, toggle selection mode between normal, flag, and question mark.

    "event" input allows function to be called by event handlers.
    """
    global mode, photos, gameover
    if gameover:
        return
    mode = (mode + 1) % 3
    if mode:
        if mode == 1:
            img = 'flag'
        else:
            img = 'question'
    else:
        img = 'blank'
    mode_select.config(image=photos[img])
    return

def update_flags():
    """
    Update the counter for how many mines have been marked.

    Note, this counts remaining mines according to what the player marks, not
    according to how many mines have/have not been correctly marked.
    """
    global MINES, flags
    flagcount.config(text="Remaining Mines:\n"+str(MINES-flags))
    if flags == MINES:
        check_win()
    return

def check_win():
    """
    Check if the player won the game.

    Does not return anything.
    """
    global gameboard

    for row in gameboard:
        for tile in row:
            if tile.is_mine:
                if not tile.is_flag():
                    return
    game_won()
    return

def game_won():
    """
    Executes when the player wins the game.
    """
    global gameboard, gameover, elapsed, difficulty
    score = elapsed
    gameover = True
    for row in gameboard:
        for tile in row:
            if not tile.is_mine:
                tile.flip()
    print ('Game Won!')
    # if difficulty == "expert":
    #     names, scores = load_scores()
    #     if score < max(scores) or len(scores) < 10:
    #         get_player_name(score)

    return

def lose():
    """
    Executes when player loses the game.
    """
    global gameboard, gameover
    gameover = True

    np.vectorize(lambda x: len(x.flip()))(gameboard)

    print ("Game Over, You Lose!")

def time_str(elapsed):
    """
    Returns the "min:sec" string for the elapsed number of seconds.
    """
    return f"{elapsed // 60}:{elapsed % 60:02d}"

def timer_update():
    """
    Update the game timer every second.
    """
    global elapsed, gameover, gametimer, paused
    if not gameover and not paused:
        elapsed += 1
        timer.config(text=time_str(elapsed))
    gametimer = timer.after(1000, timer_update)
    return

def restart(event=0):
    """
    On button click, resets game and time.

    "event" input allows function to be called by event handlers.
    """
    global gameboard, flags, gameover, HEIGHT, WIDTH, MINES, gametimer, elapsed, paused
    timer.after_cancel(gametimer)
    for child in board.winfo_children():
        child.destroy()
    gameboard = create_board(HEIGHT, WIDTH, MINES)

    flags = 0
    gameover = False
    paused = False

    update_flags()

    elapsed = -1
    timer_update()
    return

def instruct(event=0):
    """
    Opens the instructions menu.

    "event" input allows function to be called by event handlers.
    """
    global paused
    instruction_txt = "Welcome to Minesweeper!\n\nThe object of this game is relatively simple, " \
                      "all you need to do is figure out where all the mines are. Click on a tile to reveal what it is; " \
                      "if it's a mine you lose. If it's not a mine it will tell you the number of squares " \
                      "surrounding that are mines.\n\nOnce you know that a square is a mine, mark it with a flag. " \
                      "You can do this by either right clicking the square or by toggling the mode by either pressing " \
                      "the 'Mode' button or pressing the space bar (Current mode is indicated by the image on the 'Mode' " \
                      "button on the right side of the screen).\n\nThe number of remaining mines tells you how many " \
                      "flags you still need to place, however if you placed a flag incorrectly the game won't tell " \
                      "you, so be careful!\n\nGood luck!"
    p = False
    if not paused:
        p = True
        pause_game()

    inst = Toplevel()
    inst.title("Instructions")
    msg = Message(master=inst, text=instruction_txt)
    msg.pack()

    exit_game = Button(master=inst, text="Got It!", command=inst.destroy)
    exit_game.pack(pady=5)
    inst.wait_window(window=inst)
    if p and paused:
        pause_game()
    return

def pause_game(event=0):
    """
    Pauses/unpauses the game. While paused, the player can only interact with the control buttons.
    """
    global paused
    paused = not paused
    if paused:
        state.config(text='Paused')
        pause.config(relief=SUNKEN, overrelief=SUNKEN)
    else:
        state.config(text='')
        pause.config(relief=RAISED, overrelief=FLAT)
    return

def cheat_handler(event):
    """
    Handler for detecting entry of cheatcode.
    """
    global cheatstring
    char = event.char
    if char != '':
        cheatstring += char
        cheatstring = cheatstring[1:]
        if cheatstring == "danfay":
            cheat()
            cheatstring = "aaaaaa"
    return

def cheat():
    """
    Toggles cheat feature. Used primarily for debugging, but can also be implemented to create cheat codes.
    """
    global cheating, gameboard, auto
    cheating = not cheating
    if cheating:
        auto.grid()
    else:
        auto.grid_remove()
    return

def load_scores():
    """
    Load high scores from text file.
    """
    names = []
    scores = []
    data = open(".\\high_scores.txt", 'r')
    for line in data.readlines():
        score = line.split(",")
        names.append(score[0])
        scores.append(int(score[1]))
    data.close()
    return names, scores

def high_scores():
    """
    Open a window to view high scores.
    """
    global paused
    p = False
    if not paused:
        p = True
        pause_game()

    names, scores = load_scores()
    high = Toplevel()
    high.title("High Scores!")
    count = 0
    frame = Frame(master=high)
    frame.grid(padx=10, pady=10)

    head = Label(master=frame, text="High Scores!")
    head.grid(row=0, columnspan=3)

    c1 = LabelFrame(master=frame, width=50)
    c2 = LabelFrame(master=frame, width=100)
    c3 = LabelFrame(master=frame, width=50)
    c1.grid(column=0, row=1, rowspan=10)
    c2.grid(column=1, row=1, rowspan=10)
    c3.grid(column=2, row=1, rowspan=10)

    for name, score in zip(names, scores):
        num = Label(master=c1, text=str(count + 1), relief=SUNKEN, padx=10, pady=5)
        pname = Label(master=c2, text=name, relief=SUNKEN, padx=10, pady=5)
        pscore = Label(master=c3, text=time_str(score), relief=SUNKEN, padx=10, pady=5)

        num.grid(row=count, sticky=W+E)
        pname.grid(row=count, sticky=W+E)
        pscore.grid(row=count, sticky=W+E)
        count += 1

    done = Button(master=high, text="Exit", overrelief=FLAT, command=high.destroy)
    done.grid(row=count, column=0, pady=10)

    high.wait_window(window=high)
    if p and paused:
        pause_game()
    return

def add_high_score(name, score):
    """
    Add a score and name to the high score list.
    """
    names, scores = load_scores()
    for i in range(len(scores)):
        if score < scores[i]:
            scores.insert(i, score)
            names.insert(i, name)
            break
    if len(scores) > 10:
        scores.pop()
        names.pop()

    strg = ''
    for name, score in zip(names, scores):
        strg += name + ',' + str(score) + '\n'

    data = open(".\\high_scores.txt", 'w')
    data.truncate()			# Overwrite existing file

    data.write(strg)
    data.close()

    high_scores()
    return

def get_player_name(score):
    """
    Get a name and pass that name and the score to add_high_scores.
    """
    get_name = Toplevel()
    frame = Frame(master=get_name)
    frame.grid()

    txt = StringVar()
    head = Label(master=frame, text="Enter Your Name To Be Added To The High Scores!")
    head.grid()

    inp = Entry(master=frame, width=100, textvariable=txt)
    inp.grid(row=1)

    enter = Button(master=frame, text="Done", command=get_name.destroy)
    enter.grid(row=2)

    get_name.wait_window(window=get_name)
    add_high_score(txt.get(), score)

def neighbors(tile, game_board):
    """
    Return a list of the neighbors of a given tile in board.
    """
    pos = tile.get_pos()

    coords = list(filter(lambda x: np.all(np.array((0,0)) <= x) and np.all(x < np.array(gameboard.shape)),
                    [tuple(np.add(pos,(i,j))) for i in range(-1,2)
                                   for j in range(-1,2) if i or j]))

    return {gameboard[x] for x in coords}

class Modes:
    @staticmethod
    def beginner():
        """
        Starts a new game with beginner difficulty settings.
        """
        global HEIGHT, WIDTH, MINES, difficulty
        HEIGHT = 8
        WIDTH = 8
        MINES = 10
        difficulty = "beginner"
        restart()

    @staticmethod
    def intermediate():
        """
        Starts a new game with intermediate difficulty settings.
        """
        global HEIGHT, WIDTH, MINES, difficulty
        HEIGHT = 16
        WIDTH = 16
        MINES = 40
        difficulty = "intermediate"
        restart()

    @staticmethod
    def expert():
        """
        Starts a new game with expert difficulty settings.
        """
        global HEIGHT, WIDTH, MINES, difficulty
        HEIGHT = 30
        WIDTH = 16
        MINES = 99
        difficulty = "expert"
        restart()


def get_cluster(game_board, node, curnodes):
    nbrs = list(filter(lambda x: not x.flipped and x not in curnodes, neighbors(node, game_board)))
    for nbr in nbrs:
        curnodes.append(nbr)
    for nbr in nbrs:
        get_cluster(game_board, nbr, curnodes)



def ai_playgame(event=None):
    """
    Automated solver.
    """

    q = deque([])
    others = []

    while True:
        changed = False
        for i in np.ndindex(*gameboard.shape):
            if gameboard[i].flipped: q.append(gameboard[i])

        while q:
            tile = q.pop()
            if tile.get_mines_near():
                n = tile.get_mines_near()
                nbrs = neighbors(tile, gameboard)

                if n and sum(map(lambda x: not x.flipped, nbrs)) == n:
                    for nbr in filter(lambda x: not (x.flipped or x.is_flag()), nbrs):
                        nbr.set_flag(True)
                        q.extend(neighbors(nbr, gameboard))
                        changed = True
                elif n and sum(map(lambda x: x.is_flag(), nbrs)) == n:
                    for nbr in filter(lambda x: not (x.flipped or x.is_flag()), nbrs):
                        q.extend(nbr.flip())
                        q.extend(neighbors(nbr, gameboard))
                        changed = True
                elif n: others.append(tile)

            # After all easy solutions have been exhausted, attempt harder ones
            while others:
                tile = others.pop()
                n = tile.get_mines_near()
                nbrs = neighbors(tile, gameboard)
                unflipped, flipped = list(filter(lambda x: not x.flipped, nbrs)), list(filter(lambda x: x.flipped, nbrs))

                if unflipped and flipped:
                    for nbr in flipped:
                        n2 = nbr.get_mines_near()
                        nbrs2 = list(filter(lambda x: not x.flipped, neighbors(nbr, gameboard)))
                        shared = set(unflipped).intersection(set(nbrs2))

                        if shared == set(nbrs2) or min(map(lambda x: x.is_flag(), set(nbrs2).difference(shared))):
                            n3 = n - (n2 - sum(map(lambda x: x.is_flag(), set(nbrs2).difference(shared))))
                            not_shared = set(unflipped).difference(shared)
                            if n3 == sum(map(lambda x: x.is_flag(), not_shared)):
                                for t in not_shared:
                                    if not t.is_flag():
                                        q.extend(t.flip())
                                        changed = True
        if not changed: break

    # Fuck
    ### Identify clusters of tiles and attempt to analyze probabilities
    tiles = [gameboard[i] for i in np.ndindex(*gameboard.shape)
             if not gameboard[i].flipped and not gameboard[i].is_flag()]
    print(len(tiles))
    all_clusters = []
    while tiles:
        tile = tiles.pop()
        if not filter(lambda x: not x.flipped and not x.is_flag(), neighbors(tile, gameboard)): continue
        cluster = []
        get_cluster(gameboard, tile, cluster)
        if filter(lambda x: not x.is_flag(), cluster):
            all_clusters.append(
                list(filter(lambda x:
                            max(map(lambda y: y.flipped, neighbors(x, gameboard))),
                            cluster))
            )
        for t in cluster:
            if t in tiles: tiles.remove(t)






# Initialize a new window and add a frame
root = Tk()	
root.title("Minesweeper!")
board = Frame(master=root, height=750, width=256)
board.grid(padx=5, pady=5, rowspan=10)


# Store each image used as a tkinter photo object, mapped to its file name.
for filename in files:
    with Image.open(".\\Sprites\\" + filename + ".png") as image:
        photos[filename] = ImageTk.PhotoImage(image)


# Set space bar to toggle selection modes.
root.focus_set()
root.bind("<space>", toggle_mode)
root.bind("<Key>", cheat_handler)
root.bind("r", restart)

# Options Menu
menubar = Menu(root, tearoff=0)
options = Menu(menubar, tearoff=0)
options.add_command(label="Beginner", command=Modes.beginner)
options.add_command(label="Intermediate", command=Modes.intermediate)
options.add_command(label="Expert", command=Modes.expert)
options.add_separator()
options.add_command(label="Restart Game", command=restart)
options.add_separator()
options.add_command(label="Exit", command=root.destroy)
menubar.add_cascade(label="Options", menu=options)

help = Menu(menubar, tearoff=0)
help.add_command(label="Instructions", command=instruct)
help.add_command(label="High Scores", command=high_scores)
menubar.add_cascade(label="Info", menu=help)

root.config(menu=menubar)


# gameboard is a 2D array of Tile objects.
gameboard = create_board(HEIGHT, WIDTH, MINES)

# Setup additional game components to the right of the gameboard
info = Label(master=root, image=photos['mine_image'], text="Minesweeper!\nCreated By: Daniel Fay", compound=TOP)
info.grid(column=WIDTH, row=0, columnspan=4, pady=10, padx=5)


# Parent frame for game controls
controls = LabelFrame(master=root, background='Black')
controls.grid(column=WIDTH, row=2, padx=10, columnspan=4)

# Button to toggle selection modes
mode_select = Button(master=controls, width=60, height=40, text='Mode', image=photos['blank'], compound=BOTTOM, command=toggle_mode, overrelief=FLAT)
mode_select.grid(columnspan=2, rowspan=2, sticky=W+E+N+S, pady=2, padx=2)

# Displays elapsed game time
timer = Label(master=controls,text=time_str(elapsed), relief=RIDGE)
timer.grid(sticky=W+E, pady=2, padx=2)
gametimer = timer.after(1000, timer_update)

# Displays how many flags remain (ie, how many mines are unmarked assuming all flags correctly mark a mine)
flagcount = Label(master=controls, text="Remaining Mines:\n"+str(MINES - flags), relief=RIDGE)
flagcount.grid(rowspan=2, sticky=W+E, pady=2, padx=2)

# Pauses the game
pause = Button(master=controls, text="Pause", command=pause_game, overrelief=FLAT)
pause.grid(sticky=W+E, pady=2, padx=2)

# Displays whether the game is currently paused
state = Label(master=root, text='')
state.grid(row=1, column=WIDTH, columnspan=4)


auto = Button(master=controls, text="Autocomplete", command=ai_playgame, overrelief=FLAT)
auto.grid(sticky=W+E, pady=2, padx=2)
# auto.grid_remove()


root.mainloop()