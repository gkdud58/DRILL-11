from pico2d import load_image, get_time, SDL_KEYDOWN, SDL_KEYUP, SDLK_SPACE, SDLK_LEFT, SDLK_RIGHT
from transitions import Machine
import math
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))


class AutoRun:
    # 자동 무적 런 상태: 키 입력 없이 좌우로 계속 달리며, 빠르고 크다
    SPEED = 10
    SCALE = 2
    DURATION = 5.0

    def __init__(self, boy):
        self.boy = boy
        self.start_time = 0

    def enter(self):
        self.boy.frame = 0
        self.boy.dir = self.boy.face_dir
        self.start_time = get_time()

    def exit(self):
        self.boy.dir = 0

    def do(self):
        boy = self.boy
        boy.frame = (boy.frame + 1) % 8
        boy.x += boy.dir * AutoRun.SPEED
        # 화면 좌우 끝에서 자동 방향 전환
        if boy.x >= 800:
            boy.x = 800
            boy.dir = -1
        elif boy.x <= 0:
            boy.x = 0
            boy.dir = 1
        boy.face_dir = boy.dir
        if get_time() - self.start_time >= AutoRun.DURATION:
            boy.time_out()

    def draw(self):
        boy = self.boy
        row = 100 if boy.face_dir == 1 else 0
        size = 100 * AutoRun.SCALE
        # 커진 만큼 발이 땅에 붙도록 y 보정
        boy.image.clip_draw(boy.frame * 100, row, 100, 100,
                            boy.x, boy.y + (size - 100) / 2, size, size)


class Boy:
    # 상태 목록
    states = ['IDLE', 'SLEEP', 'RUN', 'AUTORUN']
    RUN_SPEED = 5

    def __init__(self):
        self.x, self.y = 400, 90
        self.frame = 0
        self.face_dir = 1
        self.dir = 0
        self.idle_start_time = 0
        self.keys = []  # 눌려 있는 방향키 (나중에 누른 키가 뒤에 온다)
        self.image = load_image('animation_sheet.png')
        self.auto_run = AutoRun(self)

        # transitions 라이브러리로 상태 기계 구성
        self.machine = Machine(model=self, states=Boy.states,
                               initial='IDLE', auto_transitions=False)
        # IDLE 상태에서 5초가 지나면 SLEEP 상태로 전이
        self.machine.add_transition('time_out', 'IDLE', 'SLEEP')
        # IDLE 상태에서 'a' 키를 누르면 AUTORUN 상태로 전이
        self.machine.add_transition('a_down', 'IDLE', 'AUTORUN')
        # AUTORUN 상태에서 5초가 지나면 IDLE 상태로 전이
        self.machine.add_transition('time_out', 'AUTORUN', 'IDLE')
        # SLEEP 상태에서 스페이스바를 누르면 다시 IDLE 상태로 전이
        self.machine.add_transition('space_down', 'SLEEP', 'IDLE')
        # IDLE / SLEEP 상태에서 좌우 키를 누르면 RUN 상태로 전이
        # AUTORUN 상태에서 누르면 무적 런이 취소되고 눌린 방향의 RUN 상태가 된다
        self.machine.add_transition('start_run', ['IDLE', 'SLEEP', 'AUTORUN'], 'RUN')
        # RUN 상태에서 방향키를 모두 떼면 IDLE 상태로 전이
        self.machine.add_transition('stop_run', 'RUN', 'IDLE')
        # 초기 상태는 on_enter 콜백이 호출되지 않으므로 직접 시작 시각 기록
        self.on_enter_IDLE()

    # --- IDLE 상태: 제자리에서 가만히 있는다 (위치 변화 없음, 서 있는 모션만 재생)
    def on_enter_IDLE(self):
        self.frame = 0
        self.idle_start_time = get_time()

    # --- SLEEP 상태: 누워서 잔다
    def on_enter_SLEEP(self):
        self.frame = 0

    # --- RUN 상태: 바라보는 방향으로 달린다
    def on_enter_RUN(self):
        self.frame = 0
        self.apply_dir()

    # --- AUTORUN 상태: 동작은 AutoRun 클래스에 위임
    def on_enter_AUTORUN(self):
        self.auto_run.enter()

    def on_exit_AUTORUN(self):
        self.auto_run.exit()

    def apply_dir(self):
        # 가장 최근에 누른 방향키를 따른다
        self.dir = self.keys[-1] if self.keys else 0
        if self.dir != 0:
            self.face_dir = self.dir

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_SPACE:
                # 자고 있을 때만 깨어난다 (IDLE에서는 무시)
                if self.state == 'SLEEP':
                    self.space_down()
            elif event.key in (SDLK_LEFT, SDLK_RIGHT):
                d = 1 if event.key == SDLK_RIGHT else -1
                if d not in self.keys:
                    self.keys.append(d)
                if self.state == 'RUN':
                    self.apply_dir()
                else:
                    self.start_run()
        elif event.type == SDL_KEYUP and event.key in (SDLK_LEFT, SDLK_RIGHT):
            d = 1 if event.key == SDLK_RIGHT else -1
            if d in self.keys:
                self.keys.remove(d)
            if self.state == 'RUN':
                if self.keys:
                    self.apply_dir()
                else:
                    self.stop_run()

    def update(self):
        if self.state == 'RUN':
            self.frame = (self.frame + 1) % 8
            self.x = max(0, min(800, self.x + self.dir * Boy.RUN_SPEED))
        elif self.state == 'IDLE':
            self.frame = (self.frame + 1) % 8
            if get_time() - self.idle_start_time >= 5.0:
                self.time_out()
        elif self.state == 'SLEEP':
            self.frame = (self.frame + 1) % 8

    def draw(self):
        if self.state == 'SLEEP':
            # 서 있는 모습을 90도 눕혀서 그린다 (얼굴이 위로 오도록 = 천장을 보고 누움)
            if self.face_dir == 1:
                self.image.clip_composite_draw(self.frame * 100, 300, 100, 100,
                                               math.pi / 2, '', self.x, self.y - 25, 100, 100)
            else:
                self.image.clip_composite_draw(self.frame * 100, 200, 100, 100,
                                               -math.pi / 2, '', self.x, self.y - 25, 100, 100)
        elif self.state == 'RUN':
            row = 100 if self.face_dir == 1 else 0
            self.image.clip_draw(self.frame * 100, row, 100, 100, self.x, self.y)
        elif self.face_dir == 1:
            self.image.clip_draw(self.frame * 100, 300, 100, 100, self.x, self.y)
        else:
            self.image.clip_draw(self.frame * 100, 200, 100, 100, self.x, self.y)
