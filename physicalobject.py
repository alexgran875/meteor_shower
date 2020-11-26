import pyglet
from pyglet.window import key
from brain import Brain

class PhysicalObject(pyglet.sprite.Sprite):

    def __init__(self, human_controlled=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.human_controlled = human_controlled
        if human_controlled:
            self.key_handler = key.KeyStateHandler()
        else:
            self.brain = Brain()

        # properties
        self.sight = 10
        self.speed = 200

        # rewards and fitness
        self.fitness = 0
        self.survival_time_without_reward = 15
        self.death_punishment = 100
        self.alive_reward = 0   # added everytime update is called as long as self.dead is False
        self.gate_reward = 100
        self.lap_reward = 10000

        # state
        self.collisions = [0, 0, 0, 0, 0, 0, 0, 0]
        self.last_collisions = self.collisions
        self.last_decisions = self.brain.make_decisions(ray_point_collisions=self.collisions)
        self.time_since_reward = 0
        self.dead = False

        # reward gates
        self.next_gate = 0  # index to keep track of the next reward gate (prevents skipping of reward gates)
        self.reward_gates = [
            # [(x bounds), (y bounds)]
            [(0,100), (100,110)],
            [(0,100), (200,210)],
            [(0,100), (400,410)],
            [(0,100), (700,710)],

            [(100,110), (700, 800)],
            [(200,210), (700, 800)],
            [(400,410), (700, 800)],
            [(700,710), (700, 800)],

            [(700, 800), (690, 700)],
            [(700, 800), (390, 400)],
            [(700, 800), (190, 200)],
            [(700, 800), (90, 100)],

            [(690, 700), (0, 100)],
            [(390, 400), (0, 100)],
            [(190, 200), (0, 100)],
            [(90, 100), (0, 100)],
        ]


    def reset(self):
        self.dead = False
        self.time_since_reward = 0
        self.fitness = 0
        self.next_gate = 0
        self.x = 50
        self.y = 50
        self.collisions = [0, 0, 0, 0, 0, 0, 0, 0]
        self.last_collisions = self.collisions
        self.last_decisions = self.brain.make_decisions(ray_point_collisions=self.collisions)
        self.visible = True

    """
        check if self is within the bounds of a reward gate and if so add
        the corresponding reward. when a lap is finished resets the next_gate index.
        also adds the alive_reward everytime the method is called.
    """
    def update_fitness(self):
        x_bounds = self.reward_gates[self.next_gate][0]
        y_bounds = self.reward_gates[self.next_gate][1]
        self.fitness += self.alive_reward

        if x_bounds[0]<=self.x<=x_bounds[1] and y_bounds[0]<=self.y<=y_bounds[1]:
            self.fitness += self.gate_reward
            self.time_since_reward = 0

            # if lap complete reset next_gate index
            if self.next_gate == len(self.reward_gates)-1:
                self.next_gate = 0
                self.fitness += self.lap_reward
            else:
                self.next_gate += 1

    """
        method for moving self using the keyboard keys
    """
    def move_human(self, dt):
        constant = int(self.speed * dt)

        if self.key_handler[key.LEFT]:
            self.x -= constant

        if self.key_handler[key.RIGHT]:
            self.x += constant

        if self.key_handler[key.UP]:
            self.y += constant

        if self.key_handler[key.DOWN]:
            self.y -= constant

    """
        method for moving self using its neural net
    """
    def move_ai(self, dt):
        constant = int(self.speed * dt)

        # if the collision state hasn't changed, use the decision from the last update
        if self.collisions == self.last_collisions:
            decisions = self.last_decisions
        else:   # if the the collision has changed, make a new decision and make that the most recent decision
            decisions = self.brain.make_decisions(ray_point_collisions=self.collisions)
            self.last_decisions = decisions

        # if zero, don't move on that axis
        if decisions[0][0] < 0:
            self.x -= constant
        elif decisions[0][0] > 0:
            self.x += constant
        #else:
        #    self.x += int(randint(-1,1) * constant)

        if decisions[0][1] < 0:
            self.y -= constant
        elif decisions[0][1] > 0:
            self.y += constant
        #else:
        #    self.y += int(randint(-1, 1) * constant)


    def move(self, dt):
        if self.human_controlled:
            self.move_human(dt)
        else:
            self.move_ai(dt)

    def update(self, dt):
        if self.dead:
            return

        self.time_since_reward += dt*3

        self.update_raypoint_collisions()

        self.move(dt)

        # if they die, they get punished
        if self.is_dead():
            self.dead = True
            self.fitness -= self.death_punishment
            self.visible = False
        elif self.time_since_reward >= self.survival_time_without_reward:
            # if they haven't received any rewards in a long time they still die, but without punishment
            self.dead = True
            self.visible = False

        self.update_fitness()


    """
        returns true if the point is overlapping with the inner wall or the game window
        (this is hardcoded for the current map and window size)
    """
    def is_point_colliding(self, point):
        if ( (100<=point[0]<=700 and 100<=point[1]<=700) or # inner wall
            (point[0]<=0) or    # left wall
            (800<=point[0]) or  # right wall
            (point[1]<=0) or       # bottom wall
            (800<=point[1])   # top wall
        ):
            return True
        else:
            return False

    """
        returns true if one of the corners are colliding or if self hasn't received
        a reward in a long time (self.survival_time_without_reward)
    """
    def is_dead(self):
        pt1 = (self.x-(self.width/2), self.y+(self.height)/2)
        pt2 = (pt1[0]+self.width, pt1[1])
        pt3 = (pt2[0], pt2[1]-self.height)
        pt4 = (pt3[0]-self.width, pt3[1])

        corner_points = [pt1, pt2, pt3, pt4]

        for point in corner_points:
            if self.is_point_colliding(point):
                return True

        return False

    """
        updates self.collisions array based on raypoint collision
        1: collision detected 
        0: collision not detected
    """
    def update_raypoint_collisions(self):
        hw = (self.width/2)
        hh = (self.height/2)

        pt1 = (self.x-hw-self.sight, self.y)
        pt2 = (pt1[0], pt1[1]+hh+self.sight)

        pt3 = (self.x, self.y+hh+self.sight)
        pt4 = (pt3[0]+hw+self.sight, pt3[1])

        pt5 = (self.x+hw+self.sight, self.y)
        pt6 = (pt5[0], pt5[1]-hh-self.sight)

        pt7 = (self.x, self.y - hh - self.sight)
        pt8 = (pt7[0] - hw - self.sight, pt7[1])

        ray_points = [pt1, pt2, pt3, pt4, pt5, pt6, pt7, pt8]

        colliding = []

        for point in ray_points:
            colliding.append(1 if self.is_point_colliding(point) else 0)

        # keep track of the last collision state to compare whether new decisions need to be made
        self.last_collisions = self.collisions
        self.collisions = colliding # new collision state

