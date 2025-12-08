import sys
import math
import random
import os
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

# ============================================================================
# 1. CONFIGURATION & GLOBAL STATE
# ============================================================================

# [REQ 6] Deverá haver pelo menos duas fontes de iluminação.
# Mude estes valores (x, y, z, w) para alterar a posição da luz. 修改这些坐标 (x, y, z, w) 可以改变光源位置。
light0_pos = [0.0, 50.0, 0.0, 1.0]   # Luz Ambiente/Sol (环境光)
light1_pos = [0.0, 6.0, -15.0, 1.0]  # Luz da Garagem (车库灯)

# --- Car State ---
car_pos = [0.0, 0.0, 0.0]    
car_yaw = 0.0                
steering_angle = 0.0         
wheel_rotation = 0.0         
car_door_open = False        
car_door_angle = 0.0         
headlights_on = False        

# --- Scene State ---
garage_door_height = 0.0     
is_night = False             

# --- Physics Constants ---
WHEELBASE = 2.8              
MAX_STEER = 35.0             # [修改说明]: 改大这个值可以让车转弯更急 (Aumentar para virar mais rápido).
STEER_SPEED = 3.0            
MOVE_SPEED = 0.5              # [修改说明]: 改大这个值可以让车跑得更快 (Aumentar para o carro andar mais rápido).

# [REQ 8] A posição da câmara deverá poder ser controlada pelo utilizador.
# 0=Orbital, 1=Seguir, 2=Condutor. O utilizador muda com a tecla 'v'. 0=轨道视角, 1=跟随视角, 2=驾驶员视角。用户按 'v' 键切换。
# - cam_dist: 修改初始摄像机距离 (Distância inicial da câmera).
camera_mode = 0 
cam_yaw = 0.0
cam_pitch = 0.2
cam_dist = 22.0

# --- Input ---
mouse_down = False
last_mouse_x = 0
last_mouse_y = 0

# --- Textures ---
tex_floor_id = 0
tex_wall_id = 0

# --- Optimization ---
floor_display_list = None 

# ============================================================================
# 2. TEXTURE GENERATION
# ============================================================================

def generate_mosaic_texture(width=128, height=128):
    """
    生成地面马赛克纹理.
    Gera textura de mosaico para o chão.
    """
    image = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            noise = random.randint(0, 40)
            if (x // 8 + y // 8) % 2 == 0:
                image[y, x] = [90+noise, 80+noise, 70+noise]
            else:
                image[y, x] = [70+noise, 60+noise, 50+noise]
    return image.tobytes()


def generate_brick_texture(width=64, height=64):
    """
    生成墙壁砖块纹理。
    Gera textura de tijolos para as paredes.
    """
    image = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            shift = 0 if (y//8)%2==0 else 4
            if ((x+shift)//16)%2==0:
                image[y,x]=[120,60,40] 
            else:
                image[y,x]=[100,50,30] 
            if y%8==0 or (x+shift)%16==0:
                image[y,x]=[150,150,150]
    return image.tobytes()


def init_resources():
    """
    初始化OpenGL纹理资源。
    Inicializa recursos de textura OpenGL.
    """
    global tex_floor_id, tex_wall_id
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    
    # Floor Texture
    tex_floor_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_floor_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 128, 128, 0, GL_RGB, GL_UNSIGNED_BYTE, generate_mosaic_texture())
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    # Wall Texture
    tex_wall_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_wall_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 64, 64, 0, GL_RGB, GL_UNSIGNED_BYTE, generate_brick_texture())
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

# ============================================================================
# 3. MATERIALS
# ============================================================================

# [REQ 7] Deverá haver pelo menos 5 materiais diferentes.
# cor do carro, altere glColor3f em 'car_paint_metal'. 车身颜色，修改 'car_paint_metal' 下面的 glColor3f 数值。
def set_material(mat_type):
    """
    定义材质属性（颜色、反光度）。
    Define propriedades do material (cor, reflexo, brilho).
    """
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0]) 

    if mat_type == "car_paint_metal": 
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.0, 0.05, 0.2, 1.0]) 
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.0, 0.1, 0.4, 1.0]) 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0]) # Brilho especular (高光)
        glMaterialf(GL_FRONT, GL_SHININESS, 20) 
        glColor3f(0.0, 0.3, 0.9) # Cor azul (蓝色)

    elif mat_type == "steering_leather":
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 20.0)
        glColor3f(0.7, 0.7, 0.75)

    elif mat_type == "car_door_inner":
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glColor3f(0.15, 0.15, 0.15)

    elif mat_type == "car_seat": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.3, 0.3, 0.3, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 10.0)
        glColor3f(0.1, 0.1, 0.1)

    elif mat_type == "car_inner_black": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.3, 0.3, 0.3, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 30.0)
        glColor3f(0.05, 0.05, 0.05)

    elif mat_type == "garage_metal": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.9, 0.9, 0.9, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 80.0)
        glColor3f(0.7, 0.7, 0.8)

    elif mat_type == "garage_inner_wall": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])
        glColor3f(0.3, 0.3, 0.3)

    elif mat_type == "glass": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 128.0)
        glColor4f(0.6, 0.85, 0.95, 0.3) 

    # --- Common Materials ---
    elif mat_type == "rubber": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glColor3f(0.15, 0.15, 0.15)

    elif mat_type == "wood": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glColor3f(0.4, 0.25, 0.1)

    elif mat_type == "stone": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])
        glColor3f(0.6, 0.6, 0.6)

    elif mat_type == "chrome": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.98, 0.98, 0.98, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 128.0)
        glColor3f(0.9, 0.9, 0.9)

    elif mat_type == "light_bulb_off": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        glColor3f(0.3, 0.3, 0.1)

    elif mat_type == "tail_light_off": 
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.3, 0.0, 0.0, 1.0])
        glColor3f(0.4, 0.0, 0.0)

    # --- House Materials ---
    elif mat_type == "house_wall_white":
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.2, 0.2, 0.2, 1.0])
        glColor3f(0.95, 0.95, 0.95)

    elif mat_type == "house_wall_brick":
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glColor3f(0.7, 0.3, 0.2)

    elif mat_type == "house_roof_dark":
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glColor3f(0.2, 0.2, 0.25)

    elif mat_type == "house_window":
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.9, 0.9, 0.9, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 100.0)
        glColor4f(0.4, 0.6, 0.8, 0.6)

# ============================================================================
# 4. ENVIRONMENT & LIGHTING
# ============================================================================

def update_car_lights():
    """
    更新车灯位置与方向（聚光灯），防止穿模并确保只照亮前方。
    Atualiza a posição e direção dos faróis (spotlights), evitando atravessar objetos.
    """
    if headlights_on:
        glEnable(GL_LIGHT2)
        glEnable(GL_LIGHT3)
        
        glPushMatrix()
        glTranslatef(car_pos[0], 0.35, car_pos[2])
        glRotatef(math.degrees(car_yaw), 0, 1, 0)
        
        spot_dir = [0.0, -0.2, -1.0] 
        spot_cutoff = 35.0           
        spot_exponent = 20.0         


        #Baixa atenuação para aumentar o brilho
        constant_att = 1.0
        linear_att = 0.002
        quad_att = 0.0
        
        # Left Headlight
        glLightfv(GL_LIGHT2, GL_POSITION, [-0.7, 0.35, -2.6, 1.0])
        glLightfv(GL_LIGHT2, GL_SPOT_DIRECTION, spot_dir)
        glLightf(GL_LIGHT2, GL_SPOT_CUTOFF, spot_cutoff)
        glLightf(GL_LIGHT2, GL_SPOT_EXPONENT, spot_exponent)
        glLightf(GL_LIGHT2, GL_CONSTANT_ATTENUATION, constant_att)
        glLightf(GL_LIGHT2, GL_LINEAR_ATTENUATION, linear_att)
        glLightf(GL_LIGHT2, GL_QUADRATIC_ATTENUATION, quad_att)

        # Right Headlight
        glLightfv(GL_LIGHT3, GL_POSITION, [0.7, 0.35, -2.6, 1.0])
        glLightfv(GL_LIGHT3, GL_SPOT_DIRECTION, spot_dir)
        glLightf(GL_LIGHT3, GL_SPOT_CUTOFF, spot_cutoff)
        glLightf(GL_LIGHT3, GL_SPOT_EXPONENT, spot_exponent)
        glLightf(GL_LIGHT3, GL_CONSTANT_ATTENUATION, constant_att)
        glLightf(GL_LIGHT3, GL_LINEAR_ATTENUATION, linear_att)
        glLightf(GL_LIGHT3, GL_QUADRATIC_ATTENUATION, quad_att)
        
        glPopMatrix()
    else:
        glDisable(GL_LIGHT2)
        glDisable(GL_LIGHT3)


# [REQ 9] Deverá haver um chão texturado por repetição.
# Mude "x1/2.0" para "x1/1.0" ou "x1/5.0" para alterar a frequência da repetição. 修改 glTexCoord2f 中的除数（比如把2.0改成1.0或5.0）来改变地板纹理的重复密度。
def draw_mosaic_floor():
    """ 
    绘制高精度马赛克地面（使用显示列表优化）。
    Desenha o chão de mosaico de alta precisão (otimizado com Display List).
    """
    global floor_display_list
    
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_floor_id)
    set_material("stone")
    
    if floor_display_list is None:
        floor_display_list = glGenLists(1)
        glNewList(floor_display_list, GL_COMPILE)
        
        size = 150.0
        steps = 120 
        step_size = (size * 2) / steps
        
        glNormal3f(0, 1, 0) 
        for i in range(steps):
            for j in range(steps):
                x1 = -size + i * step_size
                z1 = -size + j * step_size
                x2 = x1 + step_size
                z2 = z1 + step_size
                
                # --- Mapeamento de Textura (Texture Mapping) ---
                glBegin(GL_QUADS)
                glTexCoord2f(x1/2.0, z1/2.0); glVertex3f(x1, 0, z1)
                glTexCoord2f(x2/2.0, z1/2.0); glVertex3f(x2, 0, z1)
                glTexCoord2f(x2/2.0, z2/2.0); glVertex3f(x2, 0, z2)
                glTexCoord2f(x1/2.0, z2/2.0); glVertex3f(x1, 0, z2)
                glEnd()
        
        glEndList()
    
    glCallList(floor_display_list)
    glDisable(GL_TEXTURE_2D)


def draw_tree(x, z):
    """ 
    绘制树木。
    Desenha uma árvore. 
    """
    glPushMatrix()
    glTranslatef(x, 0, z)
    set_material("wood")
    
    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    quadric = gluNewQuadric()
    gluCylinder(quadric, 0.4, 0.4, 1.5, 10, 1)
    glPopMatrix()
    
    set_material("stone")
    glColor3f(0.0, 0.4, 0.0) 
    
    for i in range(3): 
        glPushMatrix()
        glTranslatef(0, 1.5 + i*1.2, 0)
        glRotatef(-90, 1, 0, 0)
        glutSolidCone(2.5 - i*0.6, 2.5, 12, 5)
        glPopMatrix()
        
    glPopMatrix()


def draw_rock(x, z):
    """ 
    绘制岩石。
    Desenha uma rocha. 
    """
    glPushMatrix()
    glTranslatef(x, 0.5, z)
    glRotatef(x * 10, 0, 1, 0)
    glRotatef(z * 10, 1, 0, 0)
    set_material("stone")
    glScalef(1.2, 0.8, 1.2)
    glutSolidDodecahedron()
    glPopMatrix()


# [REQ 5] Garagem com porta que abre por interacção.
# A animação depende de 'garage_door_height'.
# 车库门动画依赖于 'garage_door_height' 变量。
def draw_garage():
    """
    绘制车库，包含智能光照遮挡逻辑（防止光线穿墙）。
    Desenha a garagem com lógica inteligente de iluminação (evita vazamento de luz).
    """
    w, h, d, th = 8.0, 5.0, 10.0, 0.5
    garage_front_z = -10.0
    
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK) 

    # 1. Outer Walls (Always Lit)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_wall_id)
    set_material("stone")
    
    glBegin(GL_QUADS)
      # Back Wall
    glNormal3f(0,0,-1)
    glTexCoord2f(0,0); glVertex3f(w/2, 0, -d)
    glTexCoord2f(4,0); glVertex3f(-w/2, 0, -d)
    glTexCoord2f(4,2); glVertex3f(-w/2, h, -d)
    glTexCoord2f(0,2); glVertex3f(w/2, h, -d)
    # Left Wall
    glNormal3f(-1,0,0)
    glTexCoord2f(0,0); glVertex3f(-w/2, 0, -d)
    glTexCoord2f(4,0); glVertex3f(-w/2, 0, 0)
    glTexCoord2f(4,2); glVertex3f(-w/2, h, 0)
    glTexCoord2f(0,2); glVertex3f(-w/2, h, -d)
    # Right Wall
    glNormal3f(1,0,0)
    glTexCoord2f(0,0); glVertex3f(w/2, 0, 0)
    glTexCoord2f(4,0); glVertex3f(w/2, 0, -d)
    glTexCoord2f(4,2); glVertex3f(w/2, h, -d)
    glTexCoord2f(0,2); glVertex3f(w/2, h, 0)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)

    # 2. Inner Walls
    set_material("garage_inner_wall")
    
    is_car_inside = (-26 < car_pos[2] < -14) and (-5 < car_pos[0] < 5)
    is_car_in_front_of_garage = (car_pos[2] > garage_front_z) and (-10 < car_pos[0] < 10)
    is_door_open = (garage_door_height > 1.0) 
    
    can_light_reach_inside = is_car_inside or (is_car_in_front_of_garage and is_door_open)
    
    if not can_light_reach_inside:
        glDisable(GL_LIGHT2) # Left Headlight
        glDisable(GL_LIGHT3) # Right Headlight 

    glBegin(GL_QUADS)
    # Back Inside
    glNormal3f(0,0,1); glVertex3f(-w/2, 0, -d); glVertex3f(w/2, 0, -d); glVertex3f(w/2, h, -d); glVertex3f(-w/2, h, -d)
    # Left Inside
    glNormal3f(1,0,0); glVertex3f(-w/2, 0, 0); glVertex3f(-w/2, 0, -d); glVertex3f(-w/2, h, -d); glVertex3f(-w/2, h, 0)
    # Right Inside
    glNormal3f(-1,0,0); glVertex3f(w/2, 0, -d); glVertex3f(w/2, 0, 0); glVertex3f(w/2, h, 0); glVertex3f(w/2, h, -d)
    glEnd()

    if not can_light_reach_inside and headlights_on:
        glEnable(GL_LIGHT2)
        glEnable(GL_LIGHT3)

    glDisable(GL_CULL_FACE)

    # Roof & Door 屋顶和门
    glPushMatrix()
    glTranslatef(0, h, -d/2)
    glScalef(w+1, th, d+1)
    set_material("stone")
    glColor3f(0.3,0.3,0.3)
    glutSolidCube(1.0)
    glPopMatrix()
    

    # [REQ5: Porta da garagem abrir / 车库门打开]
    # garage_door_height controla a altura. 控制开启高度
    set_material("garage_metal")
    num_slats = 10
    slat_h = h / num_slats 
    
    for i in range(num_slats):
        base_y_pos = i * slat_h
        current_y = base_y_pos + garage_door_height
        
        if current_y < h:
            glPushMatrix()
            glTranslatef(0, current_y + slat_h/2, 0)
            glScalef(w-0.4, slat_h * 1.02, 0.1)
            glutSolidCube(1.0)
            glPopMatrix()


def draw_modern_house(x, z):
    """ 
    绘制现代风格房屋。
    Desenha a casa moderna. 
    """
    glPushMatrix()
    glTranslatef(x, 0, z)
    set_material("house_wall_white")
    
    glPushMatrix()
    glTranslatef(0, 2.0, 0)
    glScalef(6.0, 4.0, 6.0)
    glutSolidCube(1.0)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(-1.5, 5.0, 0)
    glScalef(4.0, 2.0, 5.0)
    glutSolidCube(1.0)
    glPopMatrix()
    
    set_material("house_window")
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    glVertex3f(-2.5, 3.5, 3.01); glVertex3f(2.5, 3.5, 3.01)
    glVertex3f(2.5, 0.1, 3.01); glVertex3f(-2.5, 0.1, 3.01)
    glEnd()
    
    glDisable(GL_BLEND)
    
    set_material("wood")
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    glVertex3f(1.5, 2.2, 3.02); glVertex3f(2.5, 2.2, 3.02)
    glVertex3f(2.5, 0.1, 3.02); glVertex3f(1.5, 0.1, 3.02)
    glEnd()
    
    glPopMatrix()


def draw_classic_house(x, z):
    """ 
    绘制经典风格房屋。
    Desenha a casa clássica. 
    """
    glPushMatrix()
    glTranslatef(x, 0, z)
    w, h, d = 5.0, 3.0, 4.0
    set_material("house_wall_brick")
    
    glPushMatrix()
    glTranslatef(0, h/2, 0)
    glScalef(w, h, d)
    glutSolidCube(1.0)
    glPopMatrix()
    
    set_material("house_roof_dark")
    h_roof = 2.0
    overhang = 0.4
    
    glBegin(GL_TRIANGLES)
    glNormal3f(0,0,1); glVertex3f(-w/2,h,d/2); glVertex3f(w/2,h,d/2); glVertex3f(0,h+h_roof,d/2)
    glNormal3f(0,0,-1); glVertex3f(0,h+h_roof,-d/2); glVertex3f(w/2,h,-d/2); glVertex3f(-w/2,h,-d/2)
    glEnd()
    
    glBegin(GL_QUADS)
    glNormal3f(-h_roof, w/2, 0)
    glVertex3f(-w/2-overhang, h-0.2, d/2+overhang); glVertex3f(0, h+h_roof, d/2+overhang)
    glVertex3f(0, h+h_roof, -d/2-overhang); glVertex3f(-w/2-overhang, h-0.2, -d/2-overhang)
    glNormal3f(h_roof, w/2, 0)
    glVertex3f(0, h+h_roof, d/2+overhang); glVertex3f(w/2+overhang, h-0.2, d/2+overhang)
    glVertex3f(w/2+overhang, h-0.2, -d/2-overhang); glVertex3f(0, h+h_roof, -d/2-overhang)
    glEnd()
    
    set_material("wood")
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    glVertex3f(-0.5, 2.0, d/2+0.01); glVertex3f(0.5, 2.0, d/2+0.01)
    glVertex3f(0.5, 0.0, d/2+0.01); glVertex3f(-0.5, 0.0, d/2+0.01)
    glEnd()
    
    set_material("house_window")
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    glVertex3f(-1.8, 2.0, d/2+0.01); glVertex3f(-1.0, 2.0, d/2+0.01)
    glVertex3f(-1.0, 1.0, d/2+0.01); glVertex3f(-1.8, 1.0, d/2+0.01)
    glVertex3f(1.0, 2.0, d/2+0.01); glVertex3f(1.8, 2.0, d/2+0.01)
    glVertex3f(1.8, 1.0, d/2+0.01); glVertex3f(1.0, 1.0, d/2+0.01)
    glEnd()
    
    glPopMatrix()

# ============================================================================
# 5. CAR COMPONENT DRAWING
# ============================================================================

def draw_wheel(radius, width):
    """ 
    绘制车轮。
    Desenha a roda. 
    """
    quadric = gluNewQuadric()
    glPushMatrix()
    glTranslatef(0, 0, -width/2)
    set_material("rubber")
    
    gluCylinder(quadric, radius, radius, width, 20, 1)
    gluDisk(quadric, 0, radius, 20, 1)
    
    glPushMatrix()
    glTranslatef(0, 0, width)
    gluDisk(quadric, 0, radius, 20, 1)
    glPopMatrix()
    
    set_material("chrome")
    glPushMatrix()
    glTranslatef(0, 0, width/2)
    glScalef(radius*1.6, radius*0.3, width*1.1)
    glutSolidCube(1.0)
    glPopMatrix()
    
    glPopMatrix()
    gluDeleteQuadric(quadric)


# [REQ 3] O veículo terá um volante que poderá rodar.
# A rotação é feita em 'draw_complete_car'. Aqui apenas se desenha a geometria. 旋转逻辑在 'draw_complete_car' 里，这里只是画出方向盘的形状。
def draw_steering_wheel():
    """ 
    绘制详细的方向盘。
    Desenha o volante detalhado. 
    """
    set_material("steering_leather")
    glutSolidTorus(0.04, 0.25, 12, 24)
    
    set_material("chrome")
    glPushMatrix()
    glScalef(1.0, 1.0, 0.5)
    glutSolidSphere(0.08, 12, 12)
    glPopMatrix()
    
    set_material("steering_leather")
    for angle in [90, 210, 330]:
        glPushMatrix()
        glRotatef(angle, 0, 0, 1)
        glTranslatef(0.12, 0, 0)
        glScalef(0.24, 0.04, 0.02)
        glutSolidCube(1.0)
        glPopMatrix()


def draw_seat():
    """ 
    绘制座椅。
    Desenha o banco. 
    """
    set_material("car_seat")
    
    glPushMatrix()
    glScalef(0.5, 0.15, 0.6)
    glutSolidCube(1.0)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(0, 0.4, 0.25)
    glRotatef(-10, 1, 0, 0)
    glScalef(0.5, 0.7, 0.1)
    glutSolidCube(1.0)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(0, 0.8, 0.3)
    glScalef(0.3, 0.2, 0.1)
    glutSolidCube(1.0)
    glPopMatrix()


def draw_front_body():
    """ 
    绘制车头（平滑曲面）。
    Desenha a frente do carro (superfície suave). 
    """
    set_material("car_paint_metal")
    profile = [(-2.4, 0.1), (-2.4, 0.4), (-2.0, 0.55), (-0.9, 0.65)]
    w_body = 0.95
    
    glBegin(GL_QUAD_STRIP)
    for z, y in profile:
        glNormal3f(-0.7, 0.5, 0.0)
        glVertex3f(-w_body, y, z)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, y, z)
    glEnd()
    
    glBegin(GL_QUAD_STRIP)
    for z, y in profile:
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, y, z)
        glNormal3f(0.7, 0.5, 0.0)
        glVertex3f(w_body, y, z)
    glEnd()
    
    for side in [-1, 1]:
        glBegin(GL_POLYGON)
        glNormal3f(side, 0, 0)
        for z, y in profile:
            glVertex3f(side * w_body, y, z)
        glVertex3f(side * w_body, 0.1, -0.9)
        glVertex3f(side * w_body, 0.1, -2.4)
        glEnd()
        
    set_material("car_inner_black")
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1) 
    glVertex3f(-w_body, 0.65, -0.9)
    glVertex3f(w_body, 0.65, -0.9)
    glVertex3f(w_body, 0.1, -0.9)
    glVertex3f(-w_body, 0.1, -0.9)
    glEnd()


def draw_rear_body():
    """ 
    绘制车尾。
    Desenha a traseira do carro. 
    """
    set_material("car_paint_metal")
    start_z = 1.3
    profile = [(start_z, 0.65), (2.1, 0.7), (2.1, 0.2)]
    w_body = 0.95
    
    glBegin(GL_QUAD_STRIP)
    for z, y in profile:
        glNormal3f(-0.7, 0.5, 0.0)
        glVertex3f(-w_body, y, z)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, y, z)
    glEnd()
    
    glBegin(GL_QUAD_STRIP)
    for z, y in profile:
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, y, z)
        glNormal3f(0.7, 0.5, 0.0)
        glVertex3f(w_body, y, z)
    glEnd()
    
    for side in [-1, 1]:
        glBegin(GL_POLYGON)
        glNormal3f(side, 0, 0)
        for z, y in profile:
            glVertex3f(side * w_body, y, z)
        glVertex3f(side * w_body, 0.1, 2.1)
        glVertex3f(side * w_body, 0.1, start_z)
        glEnd()
        
    set_material("car_inner_black")
    glBegin(GL_QUADS)
    glNormal3f(0, 0, -1) 
    glVertex3f(-w_body, 0.65, start_z)
    glVertex3f(w_body, 0.65, start_z)
    glVertex3f(w_body, 0.1, start_z)
    glVertex3f(-w_body, 0.1, start_z)
    glEnd()


def draw_rear_fender():
    """ 
    绘制后翼子板。
    Desenha o para-lama traseiro. 
    """
    set_material("car_paint_metal")
    z_start = 0.7
    z_end = 1.3
    y_top = 0.65
    y_bot = 0.1
    w_body = 0.95
    
    glBegin(GL_QUADS)
    glNormal3f(-0.5, 0.8, 0)
    glVertex3f(-w_body, y_top, z_end); glVertex3f(0, y_top, z_end)
    glVertex3f(0, y_top, z_start); glVertex3f(-w_body, y_top, z_start)
    glNormal3f(0.5, 0.8, 0)
    glVertex3f(0, y_top, z_end); glVertex3f(w_body, y_top, z_end)
    glVertex3f(w_body, y_top, z_start); glVertex3f(0, y_top, z_start)
    glEnd()
    
    for side in [-1, 1]:
        glBegin(GL_QUADS)
        glNormal3f(side, 0, 0)
        glVertex3f(side*w_body, y_top, z_start)
        glVertex3f(side*w_body, y_top, z_end)
        glVertex3f(side*w_body, y_bot, z_end)
        glVertex3f(side*w_body, y_bot, z_start)
        glEnd()


def draw_chassis_floor():
    """ 
    绘制底盘。
    Desenha o chassi. 
    """
    set_material("car_inner_black")
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glVertex3f(-0.95, 0.1, 1.4); glVertex3f(0.95, 0.1, 1.4)
    glVertex3f(0.95, 0.1, -0.9); glVertex3f(-0.95, 0.1, -0.9)
    glEnd()


# [REQ 2] Portas abrem por resposta a interacção.
# A rotação da porta é feita aqui: 'if car_door_open: glRotatef(...)'. 车门旋转逻辑在这里。如果想改变开门角度，修改 glRotatef 的参数 (60 或 -60)。
def draw_door_object(side):
    """ 
    绘制车门对象。
    Desenha o objeto da porta. 
    """
    set_material("car_paint_metal")
    glPushMatrix()
    glScalef(1.0, 1.0, 1.0)
    
    glBegin(GL_QUADS)
    glNormal3f(side, 0.2, 0)
    glVertex3f(0, 0.65, 0.0); glVertex3f(0, 0.1, 0.0)
    glVertex3f(0, 0.1, 1.6); glVertex3f(0, 0.65, 1.6)
    glEnd()
    
    set_material("car_door_inner")
    glBegin(GL_QUADS)
    glNormal3f(-side, 0, 0)
    glVertex3f(-side*0.05, 0.65, 1.6); glVertex3f(-side*0.05, 0.1, 1.6)
    glVertex3f(-side*0.05, 0.1, 0.0); glVertex3f(-side*0.05, 0.65, 0.0)
    glEnd()
    
    glPopMatrix()


def draw_glass_cabin():
    """ 
    绘制玻璃座舱。
    Desenha a cabine de vidro. 
    """
    set_material("glass")
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    glass_profile = [(-0.9, 0.65), (-0.2, 1.05), (0.6, 1.05), (1.4, 0.65)]
    w_body = 0.95
    w_roof = 0.65 
    
    # Left Half
    glBegin(GL_QUAD_STRIP)
    for i, (z, y) in enumerate(glass_profile):
        w = w_roof if (0 < i < 3) else w_body * 0.95
        glNormal3f(-0.5, 0.8, 0)
        glVertex3f(-w, y, z)
        glNormal3f(0.0, 1.0, 0)
        glVertex3f(0, y, z)
    glEnd()
    
    # Right Half
    glBegin(GL_QUAD_STRIP)
    for i, (z, y) in enumerate(glass_profile):
        w = w_roof if (0 < i < 3) else w_body * 0.95
        glNormal3f(0.0, 1.0, 0)
        glVertex3f(0, y, z)
        glNormal3f(0.5, 0.8, 0)
        glVertex3f(w, y, z)
    glEnd()
    
    # Side Windows
    for side in [-1, 1]:
        glBegin(GL_POLYGON)
        glNormal3f(side, 0, 0)
        for z, y in glass_profile:
            w = w_roof if (0 < glass_profile.index((z,y)) < 3) else w_body * 0.95
            glVertex3f(side * w, y, z)
        glEnd()
        
    glDisable(GL_BLEND)


def draw_complete_car():
    """ 
    组装完整车辆。
    Monta o carro completo. 
    """
    glPushMatrix()
    glTranslatef(car_pos[0], 0.35, car_pos[2])
    glRotatef(math.degrees(car_yaw), 0, 1, 0)
    
    draw_front_body()
    draw_rear_body()
    draw_rear_fender()
    draw_chassis_floor()

    # Doors
    door_hinge_z = -0.9
    door_width_offset = 0.95
    
    glPushMatrix()
    glTranslatef(-door_width_offset, 0, door_hinge_z)
    #Controla o angulo da porta. 控制开门角度越大越宽
    if car_door_open: glRotatef(-60, 0, 1, 0)
    draw_door_object(-1)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(door_width_offset, 0, door_hinge_z)
    if car_door_open: glRotatef(60, 0, 1, 0)
    draw_door_object(1)
    glPopMatrix()

    # Spoiler
    set_material("car_inner_black")
    glPushMatrix()
    glTranslatef(0, 0.75, 1.9)
    glPushMatrix()
    glTranslatef(-0.5, 0, 0); glScalef(0.1, 0.3, 0.2); glutSolidCube(1.0); glPopMatrix()
    glPushMatrix()
    glTranslatef(0.5, 0, 0); glScalef(0.1, 0.3, 0.2); glutSolidCube(1.0); glPopMatrix()
    glTranslatef(0, 0.15, 0)
    glPushMatrix()
    glScalef(2.2, 0.1, 0.5); glutSolidSphere(0.5, 20, 10); glPopMatrix()
    glPopMatrix()

    # Mirrors
    set_material("car_paint_metal")
    for s in [-1, 1]:
        glPushMatrix()
        glTranslatef(s * 0.9, 0.8, -0.7)
        glRotatef(s * -15, 0, 1, 0)
        glScalef(0.25, 0.15, 0.15)
        glutSolidSphere(1.0, 10, 10)
        glPopMatrix()

    # Light Bulbs
    if not headlights_on:
        set_material("light_bulb_off")
    else:
        glMaterialfv(GL_FRONT, GL_EMISSION, [1.0, 1.0, 0.9, 1.0])
        glColor3f(1.0, 1.0, 0.9)
        
    glPushMatrix()
    glTranslatef(-0.7, 0.3, -2.35); glScalef(0.25, 0.1, 0.1); glutSolidSphere(0.8, 10, 10); glPopMatrix()
    glPushMatrix()
    glTranslatef(0.7, 0.3, -2.35); glScalef(0.25, 0.1, 0.1); glutSolidSphere(0.8, 10, 10); glPopMatrix()
    
    # Tail lights
    if headlights_on:
        glMaterialfv(GL_FRONT, GL_EMISSION, [1.0, 0.0, 0.0, 1.0])
        glColor3f(1.0, 0.0, 0.0)
    else:
        glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])
        set_material("tail_light_off")
        
    glPushMatrix()
    glTranslatef(-0.6, 0.5, 2.1); glScalef(0.3, 0.1, 0.05); glutSolidCube(1.0); glPopMatrix()
    glPushMatrix()
    glTranslatef(0.6, 0.5, 2.1); glScalef(0.3, 0.1, 0.05); glutSolidCube(1.0); glPopMatrix()
    glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])

    # Inner parts
    set_material("car_inner_black") 
    glPushMatrix()
    glTranslatef(0.0, 0.4, 0.75) 
    glScalef(1.8, 0.4, 0.05)
    glutSolidCube(1.0)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(-0.45, 0.1, 0.35); draw_seat(); glPopMatrix()
    glPushMatrix()
    glTranslatef(0.45, 0.1, 0.35); draw_seat(); glPopMatrix()

    # [REQ 3] Volante roda (draw_steering_wheel).
    # Para rodar mais/menos, mude o multiplicador '1.5' (ex: steering_angle * 2.0). 改变方向盘旋转幅度，修改 'steering_angle * 1.5' 中的 1.5。
    glPushMatrix()
    glTranslatef(-0.45, 0.55, -0.50)
    glRotatef(20, 1, 0, 0)
    glRotatef(steering_angle * 1.5, 0, 0, 1)
    draw_steering_wheel()
    glPopMatrix()

    # [REQ 1] Rodas traseiras maiores que dianteiras.
    # [REQ 4] Rodas giram ao deslocar.
    # Rodas da frente (Radius=0.33)
    # Mude '0.33' para alterar o tamanho das rodas da frente. 修改 '0.33' 来改变前轮大小。
    for s in [-1, 1]: 
        glPushMatrix()
        glTranslatef(s*1.0, 0.0, -1.3)
        glRotatef(steering_angle, 0, 1, 0)
        glRotatef(-wheel_rotation, 1, 0, 0) # Rotação da roda (车轮自转)
        glRotatef(90, 0, 1, 0)
        draw_wheel(0.33, 0.25)
        glPopMatrix()
        
    #Rotação mais lenta para as rodas maiores 车轮转速
    rot_rear = wheel_rotation * (0.33/0.55)
    
    # Rodas de trás (Radius=0.50)
    # Mude '0.50' para alterar o tamanho das rodas de trás. 修改 '0.50' 来改变后轮大小。
    for s in [-1, 1]:
        glPushMatrix()
        glTranslatef(s*1.05, 0.15, 1.2)
        glRotatef(-rot_rear, 1, 0, 0)
        glRotatef(90, 0, 1, 0)
        draw_wheel(0.50, 0.35)
        glPopMatrix()
    
    draw_glass_cabin()
    glPopMatrix()

# ============================================================================
# 6. LOGIC & CONTROL
# ============================================================================

def set_projection():
    """ 
    设置投影矩阵。
    Configura a matriz de projeção. 
    """
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    target_fov = 65.0 if camera_mode == 2 else 45.0
    gluPerspective(target_fov, 800/600, 0.1, 300.0)
    glMatrixMode(GL_MODELVIEW)


def draw_scene():
    """ 
    主渲染函数。
    Função principal de renderização. 
    """
    set_projection()
    
    if is_night:
        glClearColor(0.05, 0.05, 0.1, 1.0)
    else:
        glClearColor(0.6, 0.8, 1.0, 1.0)
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    # [REQ 8] Controle de câmara (Camera Control)
    # Aqui define-se a posição da câmara (gluLookAt) para cada modo. 这里定义了不同模式下的摄像机位置 (gluLookAt)。
    if camera_mode == 0: 
        cx = car_pos[0] + cam_dist * math.sin(cam_yaw) * math.cos(cam_pitch)
        cy = car_pos[1] + cam_dist * math.sin(cam_pitch)
        cz = car_pos[2] + cam_dist * math.cos(cam_yaw) * math.cos(cam_pitch)
        if cy < 0.5: cy = 0.5 
        gluLookAt(cx, cy, cz, car_pos[0], car_pos[1], car_pos[2], 0, 1, 0)
        
    elif camera_mode == 1: 
        cx = car_pos[0] + 15.0 * math.sin(car_yaw + cam_yaw) * math.cos(cam_pitch)
        cz = car_pos[2] + 15.0 * math.cos(car_yaw + cam_yaw) * math.cos(cam_pitch)
        cy = car_pos[1] + 15.0 * math.sin(cam_pitch) + 2.0
        gluLookAt(cx, cy, cz, car_pos[0], car_pos[1], car_pos[2], 0, 1, 0)
        
    elif camera_mode == 2: 
        rad = car_yaw
        offset_right = -0.42
        offset_up = 1.35
        offset_back = 0.45
        eye_x = car_pos[0] + offset_right * math.cos(rad) + offset_back * math.sin(rad)
        eye_y = car_pos[1] + offset_up
        eye_z = car_pos[2] - offset_right * math.sin(rad) + offset_back * math.cos(rad)
        target_dist = 50.0
        tx = eye_x - target_dist * math.sin(rad)
        ty = eye_y - 3.0
        tz = eye_z - target_dist * math.cos(rad)
        gluLookAt(eye_x, eye_y, eye_z, tx, ty, tz, 0, 1, 0)
    
    update_car_lights()

    # Lights Luz Cor diffuse
    if is_night:
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.2, 0.3, 0.4, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.05, 0.05, 0.1, 1.0])
        glLightfv(GL_LIGHT0, GL_POSITION, [-20, 40, -20, 0])
    else:
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 0.9, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glLightfv(GL_LIGHT0, GL_POSITION, light0_pos)
    
    glLightfv(GL_LIGHT1, GL_POSITION, light1_pos)

    # Objects
    draw_mosaic_floor()
    
    random.seed(123)
    for _ in range(15):
        px, pz = random.randint(-40, 40), random.randint(-40, 40)
        if abs(px) > 8 or abs(pz) > 8: draw_tree(px, pz)
        
    for _ in range(10):
        px, pz = random.randint(-30, 30), random.randint(-30, 30)
        if abs(px) > 8 or abs(pz) > 8: draw_rock(px, pz)
    
    glPushMatrix()
    glTranslatef(0, 0, -15)
    draw_garage()
    glPopMatrix()
    
    draw_modern_house(-15, -10)
    draw_classic_house(15, -10)
    
    draw_complete_car()
    
    glutSwapBuffers()


def update(v):
    """
    更新动画状态（如车门开启）。
    Atualiza o estado da animação (ex: abertura da porta).
    """
    global car_door_angle
    target_angle = 60.0 if car_door_open else 0.0
    car_door_angle += (target_angle - car_door_angle) * 0.1
    
    glutPostRedisplay()
    glutTimerFunc(16, update, 0) 


def special_keys(k, x, y):
    """
    处理特殊按键（方向键）。
    Manipula teclas especiais (setas).
    """
    global car_pos, car_yaw, wheel_rotation, steering_angle
    
    # [REQUISITO: O volante poderá controlar o ângulo de viragem do veículo] (方向盘控制车辆转向角度)
    if k == GLUT_KEY_LEFT:
        steering_angle = min(steering_angle + STEER_SPEED, MAX_STEER)
    elif k == GLUT_KEY_RIGHT:
        steering_angle = max(steering_angle - STEER_SPEED, -MAX_STEER)
    
    move_dir = 0
    if k == GLUT_KEY_UP:
        move_dir = 1
        # [REQ 4] Rodas giram ao deslocar.
        # Para rodar as rodas mais depressa, mude '15' para '30'. 想要轮子转得更快，把 '15' 改成 '30'。
        wheel_rotation += 15 
        
    elif k == GLUT_KEY_DOWN:
        move_dir = -1
        wheel_rotation -= 15 
        
    # [REQ 5] O veículo deve poder deslocar-se.
    # Mude 'MOVE_SPEED' (no início do ficheiro) para alterar a velocidade. 修改文件开头的 'MOVE_SPEED' 来改变车速。
    if move_dir != 0:
        car_pos[0] -= move_dir * MOVE_SPEED * math.sin(car_yaw)
        car_pos[2] -= move_dir * MOVE_SPEED * math.cos(car_yaw)
        # [REQUISITO: O carro poderá virar além de se deslocar em linha recta] (车除了直线移动外还能转弯)
        car_yaw += move_dir * (MOVE_SPEED / WHEELBASE) * math.tan(math.radians(steering_angle))


def keyboard(key, x, y):
    """
    处理普通按键。
    Manipula teclas comuns.
    """
    global car_door_open, garage_door_height, cam_yaw, cam_pitch, camera_mode, steering_angle, is_night, headlights_on
    try:
        k = key.decode("utf-8").lower()
    except:
        return 
    
    # [REQ 2] Tecla para abrir porta. 打开车门
    if k=='o': car_door_open = not car_door_open 
    
    # [REQ 5] Teclas para abrir/fechar garagem. 打开车库门
    if k=='g': garage_door_height = min(garage_door_height + 0.1, 5.0) 
    if k=='f': garage_door_height = max(garage_door_height - 0.1, 0.0) 
    
    # [REQ 8] Tecla para mudar câmara. 切换视角
    if k=='v':
        camera_mode = (camera_mode + 1) % 3
        cam_yaw = 0.0
        cam_pitch = 0.4
        
    if k==' ': steering_angle = 0.0 
    if k=='n': is_night = not is_night 
    if k=='h': headlights_on = not headlights_on 


def mouse_func(button, state, x, y):
    """
    处理鼠标点击。
    Manipula cliques do mouse.
    """
    global mouse_down, last_mouse_x, last_mouse_y, cam_dist
    if button == GLUT_LEFT_BUTTON:
        mouse_down = (state == GLUT_DOWN)
        last_mouse_x, last_mouse_y = x, y
    elif button == 3:
        cam_dist = max(5.0, cam_dist - 1.0)
    elif button == 4:
        cam_dist = min(50.0, cam_dist + 1.0)
    glutPostRedisplay()


def motion_func(x, y):
    """
    处理鼠标拖动。
    Manipula movimento do mouse.
    """
    global cam_yaw, cam_pitch, last_mouse_x, last_mouse_y
    if mouse_down:
        dx = x - last_mouse_x
        dy = y - last_mouse_y
        cam_yaw += dx * 0.005
        cam_pitch += dy * 0.005
        cam_pitch = max(-1.0, min(1.0, cam_pitch))
        last_mouse_x, last_mouse_y = x, y
        glutPostRedisplay()


def init():
    """
    初始化OpenGL配置。
    Inicializa configurações OpenGL. 
    """ 
    glClearColor(0.6, 0.8, 1.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glEnable(GL_NORMALIZE)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    
    glLightfv(GL_LIGHT2, GL_DIFFUSE, [1.0, 1.0, 0.8, 1.0])
    glLightfv(GL_LIGHT3, GL_DIFFUSE, [1.0, 1.0, 0.8, 1.0])
    
    init_resources()


if __name__ == "__main__":
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutCreateWindow(b"Final Project")
    
    init()
    
    glutDisplayFunc(draw_scene)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutMouseFunc(mouse_func)
    glutMotionFunc(motion_func)
    glutReshapeFunc(lambda w,h: glViewport(0,0,w,h)) 
    glutTimerFunc(16, update, 0)
    
    print("="*60)
    print(" 🚗  DRIVING SIMULATOR - CONTROLS / CONTROLES  🚗")
    print("="*60)
    print(" [ARROWS]  Drive Car       | [SETAS] Dirigir o Carro")
    print(" [V]       Switch Camera   | [V]     Mudar Câmera")
    print(" [H]       Headlights      | [H]     Faróis")
    print(" [N]       Day/Night       | [N]     Dia/Noite")
    print(" [O]       Open Door       | [O]     Abrir Porta")
    print(" [G]       Open Garage     | [G]     Abrir Garagem")
    print(" [F]       Close Garage    | [F]     Fechar Garagem")
    print(" [SPACE]   Reset Steering  | [ESPAÇO] Resetar Direção")
    print(" [MOUSE]   Rotate View     | [MOUSE] Girar Visão")
    print(" [SCROLL]  Zoom            | [SCROLL] Zoom")
    print("="*60)
    
    glutMainLoop()