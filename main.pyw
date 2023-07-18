############## INITIALIZATION ##############

import pygame as pg
import easing_functions as easing
import win32api
import win32con
import win32gui
import ctypes
from ctypes import wintypes
import pyautogui
import draw
import glob
import json
import random
import keyboard
import clipboard

pg.init()

mode = pg.display.list_modes()[0]
windowx = mode[0]
windowy = mode[1]
transparent = (0,0,0)
clock = pg.time.Clock()
fps = 60

screen = pg.display.set_mode((windowx,windowy), pg.NOFRAME)
running = True
pg.display.set_caption('Pet')
pg.display.set_icon(pg.image.load('res/images/icon.png'))
draw.def_surface = screen

halfx = windowx//2
halfy = windowy//2

# invisible window

hwnd = pg.display.get_wm_info()["window"]
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*transparent), 0, win32con.LWA_COLORKEY)
user32 = ctypes.WinDLL("user32")
user32.SetWindowPos.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.INT, wintypes.INT, wintypes.INT, wintypes.INT, wintypes.UINT]
user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001)


# app functions

def none(*args): # dummy function
    pass

def create_new_pet(skin):
    pets.append(Pet(skin))

def new_pet_skin_chooser():
    global context_menu
    elements = []
    for i in glob.glob('skins\\*'):
        skin = Skin(i)
        elements.append(CMButton(skin.key, create_new_pet, [skin.key], image=skin.thumbnail))
    context_menu = ContextMenu((20,20), elements)

def open_selector(*args):
    global context_menu

    elements = [CMText('Hidden pets')]
    for i in hidden_pets:
        elements.append(CMButton(i.name, i.edit, image=i.thumbnail))
    
    elements.append(CMSeparator())
    elements.append(CMButton('Add new pet...', new_pet_skin_chooser))
    context_menu = ContextMenu((20,20), elements)


# app variables

just_unfocused = False
animations = [
    'idle_l',
    'idle_r',
    'walk_l',
    'walk_r',
    'grab_l',
    'grab_r',
    'fall_l',
    'fall_r',
    'ground_hit_l',
    'ground_hit_r',
    'rest_l',
    'rest_r',
    'wake_l',
    'wake_r',
    'pat_l',
    'pat_r',
]
end = [ # animations that don't loop over when ending
    'fall_l',
    'fall_r',
    'ground_hit_l',
    'ground_hit_r',
    'rest_l',
    'rest_r',
    'wake_l',
    'wake_r',
]
cur_name = ''
cur_size = 32


# app classes

class Skin:
    def __init__(self, path):
        self.path = path.replace('/','\\')
        self.key = self.path.split('\\')[-1]
        self.images = dict()
        for i in animations:
            self.images[i] = sorted(glob.glob(f'skins/{self.key}/{i}*.png'))
        if len(self.images['idle_r']) != 0:
            self.thumbnail = pg.transform.scale(pg.image.load(self.images['idle_r'][0]), (16,16))
        else:
            self.thumbnail = pg.transform.scale(pg.image.load('res/images/unknown.png'), (16,16))

class CMButton:
    def __init__(self, text, callback, args=[], danger=False, image=None):
        self.hoverable = True
        self.text = text
        self.callback = callback
        self.args = args
        self.size = 30
        self.danger = danger
        self.key = 25
        self.target = 25
        if image != None:
            self.image = pg.transform.scale(image, (16,16))
        else:
            self.image = None

    def update(self, hovered=False):
        if hovered:
            self.target = 70+int(mouse_press[0])*50
        if not hovered and self.target != 25:
            self.target = 25
        self.key += (self.target-self.key)/4

        if lmb_up and hovered:
            self.callback(*self.args)

    def draw(self, pos):
        rect = pg.Rect(pos, (200,30))
        color = (self.key,self.key,self.key) if not self.danger else (self.key*2-25,25,25)
        pg.draw.rect(screen, color, rect, 0, 7)
        if self.image != None:
            screen.blit(self.image, (rect.left+10,rect.top+7))
            draw.text(self.text, (rect.left+34,rect.center[1]), size=16, vertical_margin='m')
        else:
            draw.text(self.text, (rect.left+10,rect.center[1]), size=16, vertical_margin='m')

class CMBar:
    def __init__(self, variable, positions, position=0):
        self.hoverable = False
        self.variable = variable
        self.positions = positions
        self.position = position
        self.interpolated_pos = 0
        self.size = 30

    def update(self, hovered=False):
        self.interpolated_pos += (self.position-self.interpolated_pos)/5

        if mouse_press[0] and hovered:
            self.position = round(mouse_pos[0]-context_menu.position[0]-17)/184 # i dont know what this 17 means but it's here to make a good effect
            self.position = round(self.position*(len(self.positions)-1))
            self.position = max(min(self.position, len(self.positions)-1), 0)
            globals()[self.variable] = self.positions[self.position]

    def draw(self, pos):
        rect = pg.Rect(pos, (200,30))
        pg.draw.rect(screen, (20,20,20), rect, 0, 7)
        pg.draw.rect(screen, (50,50,50), pg.Rect(pos[0]+self.interpolated_pos/(len(self.positions)-1)*186, rect.top, 14,30), 0, 7)
        draw.text(str(self.positions[self.position]), rect.center, size=16, vertical_margin='m', horizontal_margin='m')

class CMInput:
    def __init__(self, variable, placeholder='', text=''):
        self.hoverable = False
        self.remove_on_hover = False
        self.variable = variable
        self.placeholder = placeholder
        self.size = 30
        self.text = text
        self.cursor_pos = len(text)

    def update(self, *args):
        for event in events:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_BACKSPACE:
                    try:
                        self.text = list(self.text)
                        self.text.pop(self.cursor_pos-1)
                        self.text = ''.join(self.text)
                        self.cursor_pos -= 1
                    except:
                        self.text = ''.join(self.text)

                elif event.key == pg.K_LEFT:
                    self.cursor_pos -= 1
                
                elif event.key == pg.K_RIGHT:
                    self.cursor_pos += 1

                elif event.key == pg.K_v and keys[pg.K_LCTRL]:
                    try:
                        self.text = list(self.text)
                        self.text.insert(self.cursor_pos,clipboard.paste())
                        self.text = "".join(self.text)
                        self.cursor_pos += len(clipboard.paste())
                    except Exception as e:
                        self.text = "".join(self.text)
                        pass

                elif event.key == pg.K_c and keys[pg.K_LCTRL]:
                    try:
                        clipboard.copy(self.text)
                    except Exception as e:
                        pass
                
                elif event.unicode.isprintable() and len(event.unicode) > 0:
                    try:
                        self.text = list(self.text)
                        self.text.insert(self.cursor_pos,event.unicode)
                        self.text = ''.join(self.text)
                        self.cursor_pos += len(event.unicode)
                    except:
                        pass

            if self.cursor_pos < 0:
                self.cursor_pos = 0
            if self.cursor_pos > len(self.text):
                self.cursor_pos = len(self.text)

            globals()[self.variable] = self.text

    def draw(self, pos):
        rect = pg.Rect(pos, (200,30))
        pg.draw.rect(screen, (20,20,20), rect, 0, 7)
        if len(self.text) == 0:
            draw.text(self.placeholder, (rect.left+10,rect.center[1]), (128,128,128), 16, vertical_margin='m')
        draw.text(self.text, (rect.left+10,rect.center[1]), size=16, vertical_margin='m')
        size = draw.get_text_size(self.text[0:self.cursor_pos], 16)[0]
        pg.draw.line(screen, (255,255,255), (rect.left+10+size,rect.top+5), (rect.left+10+size,rect.bottom-5))

class CMText:
    def __init__(self, text, image=None):
        self.hoverable = False
        self.text = text
        self.size = 25
        if image != None:
            self.image = pg.transform.scale(image, (16,16))
        else:
            self.image = None

    def update(self, *args):
        pass

    def draw(self, pos):
        rect = pg.Rect(pos, (200,20))
        if self.image != None:
            screen.blit(self.image, (rect.left+5,rect.top+2))
            draw.text(self.text, (rect.left+29,rect.center[1]), size=14, vertical_margin='m')
        else:
            draw.text(self.text, (rect.left+5,rect.center[1]), size=14, vertical_margin='m')

class CMSeparator:
    def __init__(self):
        self.hoverable = False
        self.size = 11

    def update(self, *args):
        pass

    def draw(self, pos):
        pg.draw.line(screen, (50,50,50), (pos[0]+5, pos[1]+5), (pos[0]+195, pos[1]+5), 2)

class ContextMenu:
    def __init__(self, position, elements, up=True):
        self.up = up
        self.position = position
        self.elements = elements
        self.size = sum([i.size for i in elements])+20
        self.recalculate_rect()

    def recalculate_rect(self):
        position = self.position if self.up else (self.position[0], self.position[1]-self.size+1)
        self.rect = pg.Rect(position,(220,self.size))
        self.ongoing = self.position[1]+10 if self.up else self.position[1]-self.size+10

    def draw(self):
        pg.draw.rect(screen, (25,25,25), self.rect, 0,14)

        ongoing = self.ongoing
        for i in self.elements:
            i.draw((self.position[0]+10,ongoing))
            ongoing += i.size

    def update(self):
        global context_menu
        ongoing = self.ongoing
        hovered = False
        
        for i in self.elements:
            rect = pg.Rect((self.position[0]+10, ongoing),(200,i.size))
            if not hovered and i.hoverable:
                hovered = rect.collidepoint(mouse_pos)
            i.update(rect.collidepoint(mouse_pos))
            ongoing += i.size

        if ((lmb_down or rmb_down or just_unfocused) and not self.rect.collidepoint(mouse_pos))\
            or (lmb_up and hovered) and context_menu == self:
                context_menu = None

class Pet:
    def __init__(self, skin_name, size=64, name=None):
        self.skin_name = skin_name
        self.size = size
        self.hsize = size//2 # hsize stands for half size, not horizontal size
        self.refresh_images()

        self.anim_index = 0
        self.anim_key = 0
        self.animation = 'idle_r'
        self.state = 'idle'
        self.state_timer = random.randint(300,700)
        self.dragging = False
        self.following = False

        self.pat_decrease_timer = 0
        self.pats = 0
        self.sleepiness = 0.005
        if name == None:
            self.name = skin_name
        else:
            self.name = name

        self.reappear()

    def edit(self):
        global context_menu
        if self in pets:
            context_menu = ContextMenu((20,20), [
                CMText(self.name, image=self.thumbnail),
                CMButton('Rename', self.rename_question),
                CMButton('Resize', self.resize_question),
                CMButton('Hide pet', self.hide, danger=True)
            ])
        else:
            context_menu = ContextMenu((20,20), [
                CMText(self.name, image=self.thumbnail),
                CMButton('Spawn', self.add),
                CMButton('Rename', self.rename_question),
                CMButton('Resize', self.resize_question),
                CMButton('Delete', self.erase_question, danger=True)
            ])

    def add(self):
        global hidden_pets, pets
        self.reappear()
        pets.append(self)
        hidden_pets.remove(self)

    def reappear(self):
        self.pos = [halfx, halfy]
        self.vel = [0, 0]
        self.recalculate_rect()
        self.size_decrease = self.size
        self.change_anim('fall_r')

    def follow_me(self):
        self.following = not self.following

    def hide(self):
        global hidden_pets, pets
        hidden_pets.append(self)
        pets.remove(self)

    def erase(self):
        global hidden_pets
        hidden_pets.remove(self)

    def erase_question(self):
        global context_menu
        context_menu = ContextMenu((20,20), [
            CMText('You sure you want to delete?'),
            CMText(self.name, image=self.thumbnail),
            CMButton('No', self.edit),
            CMButton('Yes', self.erase)
        ])

    def rename_question(self):
        global context_menu
        context_menu = ContextMenu((20,20), [
            CMText('Rename pet'),
            CMText(self.name, image=self.thumbnail),
            CMInput('cur_name', 'Name for your pet', self.name),
            CMButton('Done', self.rename)
        ])

    def rename(self):
        self.name = cur_name

    def resize_question(self):
        global context_menu
        context_menu = ContextMenu((20,20), [
            CMText('Set new size'),
            CMText(self.name, image=self.thumbnail),
            CMBar('cur_size', [16,32,48,64,80,96,112,128,144,160], ),
            CMButton('Done', self.resize)
        ])

    def resize(self):
        self.size = cur_size
        self.hsize = cur_size//2
        self.refresh_images()
        self.recalculate_rect()

    def open_context_menu(self):
        global context_menu
        if self.state == 'rest':
            context_menu = ContextMenu(mouse_pos, [
                CMText(self.name, image=self.thumbnail),
                CMButton('Settings', self.edit),
                CMSeparator(),
                CMButton('Wake up', self.wake_up),
            ], False)
        else:
            context_menu = ContextMenu(mouse_pos, [
                CMText(self.name, image=self.thumbnail),
                CMButton('Settings', self.edit),
                CMSeparator(),
                CMButton('Follow me' if not self.following else 'Stop following', self.follow_me),
                CMButton('Rest', self.send_to_rest),
            ], False)

    def recalculate_rect(self):
        self.rect = pg.Rect(self.pos[0]-self.hsize, self.pos[1]-self.size, self.size, self.size)

    def physics(self):
        if not self.dragging:
            self.vel[1] += 0.7
        
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]

        if self.pos[1] > windowy-1:
            if self.vel[1] > 25 or abs(self.vel[0]) > 20:
                self.change_anim_dir('ground_hit')
                self.state_timer = 100
                self.state = 'ground_hit'
            elif self.state in ['grab','fall'] and not self.dragging:
                self.change_anim_dir('idle')
                self.state_timer = random.randint(300,700)
                self.state = 'idle'
            self.vel[1] = 0
            self.pos[1] = windowy-1
            self.vel[0] /= 1.5
        if self.pos[1] < 0+self.hsize:
            self.vel[1] = -self.vel[1]
            self.pos[1] = 0+self.hsize
        if self.pos[0] < 0+self.hsize:
            if self.state == 'fall':
                self.change_anim('fall_r')
            self.vel[0] = -self.vel[0]/3
            self.vel[1] /= 2
            self.pos[0] = 0+self.hsize
        if self.pos[0] > windowx-self.hsize:
            if self.state == 'fall':
                self.change_anim('fall_l')
            self.vel[0] = -self.vel[0]/3
            self.vel[1] /= 2
            self.pos[0] = windowx-self.hsize

    def refresh_images(self, skin_name=None):
        if skin_name == None: skin_name = self.skin_name

        self.images = dict()
        for i in animations:
            self.images[i] = sorted(glob.glob(f'skins/{skin_name}/{i}*.png'))
        if len(self.images['idle_r']) != 0:
            self.thumbnail = pg.transform.scale(pg.image.load(self.images['idle_r'][0]), (16,16))
        else:
            self.thumbnail = pg.transform.scale(pg.image.load('res/images/unknown.png'), (16,16))
        for i in self.images:
            if len(self.images[i]) == 0:
                self.images[i] = ['res/images/unknown.png']
            self.images[i] = [pg.transform.scale(pg.image.load(j), (self.size, self.size)) for j in self.images[i]]

        with open(f'skins/{skin_name}/speed.json') as f:
            self.speeds = json.load(f)
        for i in animations:
            if i not in self.speeds:
                self.speeds[i] = 20

    def change_anim(self, new_key):
        self.anim_index = 0
        self.anim_key = 0
        self.animation = new_key

    def change_anim_dir(self, new_key):
        if self.animation.endswith('_r'):
            self.change_anim(f'{new_key}_r')
        elif self.animation.endswith('_l'):
            self.change_anim(f'{new_key}_l')
        else:
            self.change_anim(random.choice([f'{new_key}_r',f'{new_key}_l']))

    def send_to_rest(self):
        self.change_anim_dir('rest')
        self.state = 'rest'
        self.state_timer = random.randint(50000,100000)
        self.sleepiness = 0.01
        self.following = False

    def wake_up(self):
        self.state_timer = 80
        self.change_anim_dir('wake')
        self.state = 'wake'

    def draw(self):
        if self.size_decrease > 0.0:
            im = pg.transform.scale(self.images[self.animation][self.anim_index], (self.size-self.size_decrease,self.size-self.size_decrease))
            ir = im.get_rect()
            ir.center = self.rect.center
            screen.blit(im, ir)
        else:
            screen.blit(self.images[self.animation][self.anim_index], self.rect)

    def update(self):
        global dragging

        # physics and this kind of stuff
        self.recalculate_rect()
        self.physics()

        # animation
        self.anim_key += 1
        if self.anim_key > self.speeds[self.animation]:
            self.anim_index += 1
            self.anim_key = 0
        if self.anim_index >= len(self.images[self.animation]):
            if self.animation in end:
                self.anim_index = len(self.images[self.animation])-1
            else:
                self.anim_index = 0
        if self.size_decrease > 0.0:
            self.size_decrease /= 1.3
            if self.size_decrease < 0.05:
                self.size_decrease = 0.0

        # dragging
        if self.rect.collidepoint(mouse_pos) and mouse_press[0] and mouse_moved != (0,0) and not dragging\
            and not (context_menu != None and context_menu.rect.collidepoint(mouse_pos)):
                self.dragging = True
                dragging = True
                self.change_anim_dir('grab')
                self.state = 'grab'
                self.pats = 0   
        if not mouse_press[0] and self.dragging:
            self.dragging = False
            dragging = False
            self.vel[1] /= 2
            self.vel[0] /= 3
            self.change_anim_dir('fall')
            self.anim_key = 300
            self.state = 'fall'
        if self.dragging:
            self.vel[0] = mouse_moved[0]
            self.vel[1] = mouse_moved[1]

        # petting
        if self.rect.collidepoint(mouse_pos) and lmb_down and self.pats < 4:
            self.pats += 1

        if self.pats == 4:
            self.pats -= 1
            if self.state == 'rest':
                self.wake_up()
            elif self.state == 'wake':
                pass
            else:
                self.change_anim_dir('pat')
                self.state_timer = 250
                self.state = 'patting'

        if self.pats > 0:
            self.pat_decrease_timer += 1
            if self.pat_decrease_timer >= 30:
                self.pats -= 1
                self.pat_decrease_timer = 0

        # state changing
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.sleepiness += 0.0005

            if self.state == 'idle' and not self.following:
                if random.random() < self.sleepiness:
                    self.send_to_rest()

                else:
                    available = ['walk_r','walk_l']

                    if self.pos[0] < windowx/3:
                        available.remove('walk_l')
                    if windowx-self.pos[0] < windowx/3:
                        available.remove('walk_r')

                    self.state = random.choice(available)

                    if self.state == 'walk_l':
                        dst = int(self.pos[0])
                    elif self.state == 'walk_r':
                        dst = int(windowx-self.pos[0])

                    self.state_timer = random.randint(dst//5, dst//1.5)
                    self.change_anim(self.state)

            elif self.state in ['grab','fall']:
                self.state_timer = 300
            
            elif self.state == 'rest':
                self.state_timer = 80
                self.change_anim_dir('wake')
                self.state = 'wake'

            else:
                self.change_anim_dir('idle')
                self.state = 'idle'
                self.state_timer = random.randint(300,700)

        # following
        if self.following:
            if abs(mouse_pos[0]-self.pos[0]) < 75:
                if self.state in ['walk_l','walk_r']:
                    self.state = 'idle'
                    self.change_anim_dir('idle')
            elif self.state not in ['fall','grab','ground_hit']:
                self.state = 'walk_l' if mouse_pos[0] < self.pos[0] else 'walk_r'
                if self.state != self.animation:
                    self.change_anim(self.state)

        # walking
        if self.state == 'walk_l':
            self.pos[0] -= 1
        elif self.state == 'walk_r':
            self.pos[0] += 1

        # context menu
        if self.rect.collidepoint(mouse_pos) and rmb_down:
            self.open_context_menu()


# preparing

pets = [Pet('Roxy', 64)]
hidden_pets = []
rects = []
dragging = False
context_menu = None
prev_focus = True
cur_focus = True
keyboard.on_press_key('f7', open_selector)


# main loop

while running:

############## INPUT ##############

    events = pg.event.get()
    mouse_pos = pyautogui.position()
    mouse_press = pg.mouse.get_pressed(5)
    mouse_moved = pg.mouse.get_rel()
    keys = pg.key.get_pressed()

    lmb_down = False
    rmb_down = False
    lmb_up = False

    if prev_focus and not cur_focus:
        just_unfocused = True

    prev_len = len(rects)
    screen.fill((0,0,0))



############## PROCESSING EVENTS ##############

    for event in events:
        if event.type == pg.QUIT:
            running = False

        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                lmb_down = True
            if event.button == 3:
                rmb_down = True

        if event.type == pg.MOUSEBUTTONUP:
            if event.button == 1:
                lmb_up = True



############## APP LOGIC ##############

    for pet in pets:
        pet.update()
        pet.draw()
        rects.append(pet.rect)

    if context_menu != None:
        rects.append(context_menu.rect)
        context_menu.draw()
        context_menu.update()



############## UPDATING SCREEN ##############

    if rects != []:
        fps = 60
        pg.display.update(rects)
    elif fps != 5:
        fps = 5
    for i in range(prev_len):
        rects.pop(0)
    clock.tick(fps)

    prev_focus = cur_focus
    cur_focus = pg.key.get_focused()
    just_unfocused = False