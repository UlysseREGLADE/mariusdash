raspberry = False
use_image = True

import tkinter as tk
import numpy as np
import time
import os

# marius_png = "marius_30px_transparent.png"
marius_png = "marius.png"
nano_tube_png = ["nano_tube_1.png",
                 "nano_tube_2.png",
                 "nano_tube_3.png",
                 "nano_tube_4.png"]

bg_color = 'sky blue'
bg_color = 'RoyalBlue4'
bg_color = 'medium blue'
bg_color = 'navy'

gpio_left_button = 8
gpio_right_button = 10
gpio_buzzer = 16

left_keycode = 65 # key code for 'z' in tkinter
right_keycode = 90 # key code for 'a' in tkinter

screen_width = 640 # px
screen_height = 480 # px

fps = 30 # s**-1
gravity = 1000.0 # px/s**-2
jump_speed = 400.0 # px/s

character_size = 48 # px
platform_size = 32 # px
platform_length = [screen_width*0.25, screen_width*0.65] # px
platform_spacing = [screen_width/4, screen_width/2] # px
platform_relative_height = [-100, 100] # px

character_screen_x = screen_width/6

character_acc= 500.0 # px/s**-2
character_max_speed = 600.0 # px/sz

character_slow_down = 0.01 # s

game_over_screen_time = 1.0 # s

character_slow_down_air = np.exp(-character_slow_down*fps/5)
character_slow_down = np.exp(-character_slow_down*fps)

if raspberry:
    import RPi.GPIO as GPIO

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(gpio_left_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(gpio_right_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(gpio_buzzer, GPIO.OUT)

class Buzzer():
    
    def __init__(self):
        self.time = 0
        self.state = False
        self.previous_state = False
    
    def update(self):
        if self.time > 0:
            self.time -= 1/fps
            self.state = True
        else:
            self.state = False
        
        if raspberry:
            if self.state != self.previous_state:
                if self.state:
                    GPIO.output(gpio_buzzer, GPIO.HIGH)
                else:
                    GPIO.output(gpio_buzzer, GPIO.LOW)
                self.previous_state = self.state



class Input():

    def __init__(self, root):
        if not raspberry:
            self.pressed_keycodes = []

            root.bind('<KeyPress>', self.key_pressed)
            root.bind('<KeyRelease>', self.key_released)
    
    def key_pressed(self, event):
        if event.keycode not in self.pressed_keycodes:
            self.pressed_keycodes.append(event.keycode)
    
    def key_released(self, event):
        if event.keycode in self.pressed_keycodes:
            self.pressed_keycodes.remove(event.keycode)
    
    def left(self):
        if raspberry:
            return GPIO.input(gpio_left_button) == GPIO.HIGH
        else:
            return left_keycode in self.pressed_keycodes
    
    def right(self):
        if raspberry:
            return GPIO.input(gpio_right_button) == GPIO.HIGH
        else:
            return right_keycode in self.pressed_keycodes

class Game():

    def __init__(self):

        self.root = tk.Tk()
        self.w, self.h = screen_width, screen_height
        self.input = Input(self.root)
        self.buzzer = Buzzer()

        self.canvas = tk.Canvas(self.root, width=self.w, height=self.h)
        self.canvas.pack()
        self.canvas.configure(bg=bg_color)

        self.time = 0
        self.root.after(10, self.update)
        if raspberry:
            self.root.attributes("-fullscreen", True)
            self.root.config(cursor="none")

        # Load nano tube images if needed
        if use_image:
            self.nano_tube_photos = []
            self.lengths = []
            for png in nano_tube_png:
                self.nano_tube_photos.append(tk.PhotoImage(file=png))
                self.lengths.append(self.nano_tube_photos[-1].width())
        
        # Init the game
        self.status = 'splash screen'
        self.reset_game()
        
        # Load the best score
        if not os.path.exists('best_score.npy'):
            self.best_score = 0
            np.save('best_score', self.best_score)
        else:
            self.best_score = np.load('best_score.npy')
        
        # Init game graphics
        if not use_image:
            self.character = self.canvas.create_rectangle(character_screen_x-0.5*self.character_size,
                                                        self.character_y-0.5*self.character_size,
                                                        character_screen_x+0.5*self.character_size,
                                                        self.character_y+0.5*self.character_size,
                                                        fill='red')
        else:
            self.marius_photo = tk.PhotoImage(file=marius_png)
            self.character = self.canvas.create_image(character_screen_x-0.5*self.character_size,
                                                      self.character_y-0.5*self.character_size,
                                                      anchor=tk.NW,
                                                      image=self.marius_photo)

        self.platforms = []
        for i in range(self.platform_pos.shape[0]):
            if not use_image:
                platform = self.canvas.create_rectangle(self.platform_pos[i, 0],
                                                        self.platform_pos[i, 2],
                                                        self.platform_pos[i, 0]+self.platform_pos[i, 1],
                                                        self.platform_pos[i, 2]+platform_size,
                                                        fill='black')
            else:
                platform = self.canvas.create_image(self.platform_pos[i, 0],
                                                    self.platform_pos[i, 2],
                                                    anchor=tk.NW,
                                                    image=self.nano_tube_photos[i])
            self.platforms.append(platform)
        
        self.display_text = self.canvas.create_text(self.w/2, self.h/3, text="Marius Dash !", fill="white", font='Arial %i'%int(self.h/12))
        self.score_text = self.canvas.create_text(self.w*18/20, self.h*2/20, text="Score %i"%(self.character_x-character_screen_x), fill="white", font='Arial %i'%int(self.h/24), anchor='e')
        self.best_score_text = self.canvas.create_text(self.w*18/20, self.h*17/20, text="Best Score %i"%(self.best_score), fill="white", font='Arial %i'%int(self.h/20), anchor='e')
    
    def reset_game(self):
        self.ground_level = self.h/2
        self.character_size = character_size
        self.character_y = self.ground_level - self.character_size/2
        self.character_x = character_screen_x

        self.character_vx = 0
        self.character_vy = 0
        self.character_ay = gravity
        self.character_landed = True

        # left size, length, y-pos
        if not use_image:
            self.platform_pos = np.array([[self.w*1/6-32, self.w/3, self.h/2], [self.w*4/6-32, self.w/3, self.h/2]])
        else:
            self.platform_pos = np.array([[self.w*1/6-32, self.lengths[0], self.h/2], [self.w*4/6, self.lengths[1], self.h/2]])
            if hasattr(self, 'platforms'):
                self.canvas.itemconfig(self.platforms[0], image=self.nano_tube_photos[0])
                self.canvas.itemconfig(self.platforms[1], image=self.nano_tube_photos[1])
    
    def update(self):

        start_time = time.time()

        self.on_update()
        self.buzzer.update()

        loop_time = time.time() - start_time
        self.time += 1/fps
        wait_time_ms = max(10, int(1000*(1/fps - loop_time)))
        self.root.after(wait_time_ms, self.update)
    
    def on_update(self):
        if self.status == 'splash screen':
            self.update_splash_screen()
        elif self.status == 'game':
            self.update_game()
        elif self.status == 'game over':
            self.update_game_over()
    
    def update_splash_screen(self):
        if self.input.right() or self.input.left():
            self.status = 'game'
            self.canvas.itemconfig(self.display_text, text='')
            
    def update_game_over(self):
        if self.game_over_timer < 0:
            self.status = 'splash screen'
            self.canvas.itemconfig(self.display_text, text='Marius Dash !')
            self.reset_game()
            self.update_canvas()
        self.game_over_timer -= 1/fps

    def update_game(self):

        # x update

        if self.input.right() and self.character_landed:
            self.character_vx += character_acc/fps
            if self.character_vx > character_max_speed:
                self.character_vx = character_max_speed
        elif not self.input.right() and self.character_landed:
            self.character_vx = self.character_vx*character_slow_down
        elif not self.input.right():
            self.character_vx = self.character_vx*character_slow_down_air
        
        self.character_x += self.character_vx/fps

        self.platform_pos[:, 0] -= self.character_vx/fps

        if self.platform_pos[0, 0] + self.platform_pos[0, 1] < 0:
            self.platform_pos[0, :] = self.platform_pos[1, :]

            self.platform_pos[1, 0] = self.platform_pos[0, 0] + self.platform_pos[0, 1] + np.random.uniform(platform_spacing[0], platform_spacing[1])
            if not use_image:
                self.platform_pos[1, 1] = np.random.uniform(platform_length[0], platform_length[1])
            else:
                index = np.random.randint(len(self.lengths))
                self.platform_pos[1, 1] = self.lengths[index]
                self.canvas.itemconfig(self.platforms[0], image=self.nano_tube_photos[self.lengths.index(self.platform_pos[0, 1])])
                self.canvas.itemconfig(self.platforms[1], image=self.nano_tube_photos[index])
            self.platform_pos[1, 2] = np.random.uniform(platform_relative_height[0], platform_relative_height[1]) + self.platform_pos[0, 2]
            self.platform_pos[1, 2] = np.clip(self.platform_pos[1, 2], self.h/4, self.h*3/4)
        
        # update ground level

        self.ground_level = 2*self.h
        over_platform = False
        for i in range(self.platform_pos.shape[0]):
            if self.platform_pos[i, 0] < character_screen_x + 0.5*self.character_size and self.platform_pos[i, 0] + self.platform_pos[i, 1] > character_screen_x - 0.5*self.character_size:
                over_platform = True
                self.ground_level = self.platform_pos[i, 2]
        
        if not over_platform:
            self.character_landed = False
        
        # y update

        if self.input.left() and self.character_landed:
            self.character_vy = -jump_speed
            self.character_landed = False

        if not self.character_landed:
            self.character_vy += self.character_ay/fps

            if abs(self.character_vy) > self.character_size*fps:
                self.character_vy = self.character_vy*self.character_size*fps/abs(self.character_vy)
        
        self.character_y += self.character_vy/fps

        if self.character_y + self.character_size/2 > self.ground_level and self.character_y + self.character_size/2 < self.ground_level + platform_size:
            self.character_y = self.ground_level - self.character_size/2
            self.character_landed = True
            self.character_vy = 0
        
        # game over update

        if self.character_y > self.h:
            self.status = 'game over'
            if self.best_score > self.character_x-character_screen_x:
                self.canvas.itemconfig(self.display_text, text='Game Over')
                self.game_over_timer = 1

                if raspberry:
                    for i in range(3):
                        GPIO.output(gpio_buzzer, GPIO.HIGH)
                        time.sleep(0.1)
                        GPIO.output(gpio_buzzer, GPIO.LOW)
                        time.sleep(0.1)
            else:
                # update and save the best score
                self.best_score = self.character_x-character_screen_x
                np.save('best_score', self.best_score)

                random_text = np.random.choice(['',
                                                '\nZaki is proud of you !',
                                                '\nTakis gives you a\nhigh five ^^',
                                                '\nBenoit Doucot is\nconvinced !'])
                self.canvas.itemconfig(self.display_text, text='New best score !'+random_text)
                self.canvas.itemconfig(self.best_score_text, text="Best Score %i"%(self.best_score))
                self.game_over_timer = 2

                if raspberry:
                    beeps = [0.4, 0.1, 0.1, 0.1, 0.5, 0.2, 0.3]
                    silences = [0.2, 0.1, 0.1, 0.3, 0.2, 0.2, 0.1]

                    for i in range(len(beeps)):
                        GPIO.output(gpio_buzzer, GPIO.HIGH)
                        time.sleep(beeps[i])
                        GPIO.output(gpio_buzzer, GPIO.LOW)
                        time.sleep(silences[i])

        self.update_canvas()
    
    def update_canvas(self):
        if not use_image:
            self.canvas.coords(self.character,
                            character_screen_x-0.5*self.character_size,
                            self.character_y-0.5*self.character_size,
                            character_screen_x+0.5*self.character_size,
                            self.character_y+0.5*self.character_size,)
            
            for i in range(self.platform_pos.shape[0]):
                self.canvas.coords(self.platforms[i],
                                self.platform_pos[i, 0],
                                self.platform_pos[i, 2],
                                self.platform_pos[i, 0]+self.platform_pos[i, 1],
                                self.platform_pos[i, 2]+platform_size)
        else:
            self.canvas.coords(self.character,
                            character_screen_x-0.5*self.character_size,
                            self.character_y-0.5*self.character_size)
            
            for i in range(self.platform_pos.shape[0]):
                self.canvas.coords(self.platforms[i],
                                self.platform_pos[i, 0],
                                self.platform_pos[i, 2])
            
        self.canvas.itemconfig(self.score_text, text="Score %i"%(self.character_x-character_screen_x))

if __name__ == '__main__':

    game = Game()
    game.root.mainloop()