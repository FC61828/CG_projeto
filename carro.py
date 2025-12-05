import sys
import math
import random
import os
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

# ============================================================================
# 1. CONFIGURATION & GLOBAL STATE (配置与全局状态 / Configuração e Estado Global)
# ============================================================================

# --- Lighting (光照 / Iluminação) ---
# CN: 太阳/月亮光源位置
# PT: Posição da luz do Sol/Lua
light0_pos = [0.0, 50.0, 0.0, 1.0]

# CN: 车库内部光源位置
# PT: Posição da luz da garagem
light1_pos = [0.0, 6.0, -15.0, 1.0]

# --- Car State (车辆状态 / Estado do Carro) ---
car_pos = [0.0, 0.0, 0.0]    # CN: 车辆位置 / PT: Posição do veículo
car_yaw = 0.0                # CN: 车辆朝向 / PT: Rotação do veículo
steering_angle = 0.0         # CN: 方向盘角度 / PT: Ângulo do volante
wheel_rotation = 0.0         # CN: 车轮滚动角度 / PT: Rotação das rodas
car_door_open = False        # CN: 车门开关状态 / PT: Estado da porta (aberta/fechada)
car_door_angle = 0.0         # CN: 车门动画值 / PT: Valor da animação da porta
headlights_on = False        # CN: 车灯开关 / PT: Estado dos faróis

# --- Scene State (场景状态 / Estado da Cena) ---
garage_door_height = 0.0     # CN: 车库门开启高度 / PT: Altura da porta da garagem
is_night = False             # CN: 昼夜模式 / PT: Modo Dia/Noite

# --- Physics Constants (物理常数 / Constantes Físicas) ---
WHEELBASE = 2.8              # CN: 轴距 / PT: Distância entre eixos
MAX_STEER = 35.0             # CN: 最大转向角 / PT: Ângulo máximo de direção
STEER_SPEED = 3.0            # CN: 转向速度 / PT: Velocidade de direção
MOVE_SPEED = 0.5             # CN: 移动速度 / PT: Velocidade de movimento

# --- Camera (摄像机 / Câmera) ---
# 0: Orbit (外部), 1: Follow (跟随), 2: Driver (车手)
camera_mode = 0 
cam_yaw = 0.0
cam_pitch = 0.2
cam_dist = 22.0

# --- Input (输入 / Entrada) ---
mouse_down = False
last_mouse_x = 0
last_mouse_y = 0

# --- Textures (纹理 / Texturas) ---
tex_floor_id = 0
tex_wall_id = 0

# ============================================================================
# 2. TEXTURE GENERATION (纹理生成 / Geração de Texturas)
# ============================================================================

def generate_mosaic_texture(width=128, height=128):
    """
    CN: 生成地面马赛克纹理。
    PT: Gera textura de mosaico para o chão.
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
    CN: 生成墙壁砖块纹理。
    PT: Gera textura de tijolos para as paredes.
    """
    image = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            shift = 0 if (y//8)%2==0 else 4
            # Brick vs Mortar logic
            if ((x+shift)//16)%2==0:
                image[y,x]=[120,60,40] 
            else:
                image[y,x]=[100,50,30] 
            if y%8==0 or (x+shift)%16==0:
                image[y,x]=[150,150,150]
    return image.tobytes()

def init_resources():
    """
    CN: 初始化OpenGL纹理资源。
    PT: Inicializa recursos de textura OpenGL.
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
# 3. MATERIALS (材质库 / Materiais)
# ============================================================================

def set_material(mat_type):
    """
    CN: 设置材质属性（颜色、反光、高光）。
    PT: Define propriedades do material (cor, reflexo, brilho).
    """
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0]) 

    if mat_type == "car_paint_metal": 
        # CN: 蓝色金属车漆 (高光增强)。
        # PT: Pintura metálica azul (brilho aprimorado).
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.0, 0.05, 0.2, 1.0]) 
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.0, 0.1, 0.4, 1.0]) 
        # High specular for strong reflection (强烈的镜面反射)
        glMaterialfv(GL_FRONT, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0]) 
        glMaterialf(GL_FRONT, GL_SHININESS, 20) 
        glColor3f(0.0, 0.3, 0.9) 

    elif mat_type == "steering_leather":
        # CN: 浅灰色方向盘皮革。
        # PT: Couro cinza claro para o volante.
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 20.0)
        glColor3f(0.7, 0.7, 0.75)

    elif mat_type == "car_door_inner":
        # CN: 车门内饰。
        # PT: Interior da porta.
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.1, 0.1, 0.1, 1.0])
        glColor3f(0.15, 0.15, 0.15)

    elif mat_type == "car_seat": 
        # CN: 深色座椅。
        # PT: Assentos escuros.
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.3, 0.3, 0.3, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 10.0)
        glColor3f(0.1, 0.1, 0.1)

    elif mat_type == "car_inner_black": 
        # CN: 黑色塑料部件。
        # PT: Peças de plástico preto.
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.3, 0.3, 0.3, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 30.0)
        glColor3f(0.05, 0.05, 0.05)

    elif mat_type == "garage_metal": 
        # CN: 车库门金属。
        # PT: Metal da porta da garagem.
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.9, 0.9, 0.9, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 80.0)
        glColor3f(0.7, 0.7, 0.8)

    elif mat_type == "garage_inner_wall": 
        # CN: 车库内墙（无反光）。
        # PT: Parede interna da garagem (sem reflexo).
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])
        glColor3f(0.3, 0.3, 0.3)

    elif mat_type == "glass": 
        # CN: 玻璃（透明）。
        # PT: Vidro (transparente).
        glMaterialfv(GL_FRONT, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 128.0)
        glColor4f(0.6, 0.85, 0.95, 0.3) 

    # --- Common Materials (通用材质 / Materiais Comuns) ---
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

    # --- House Materials (房屋材质 / Materiais das Casas) ---
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
# 4. ENVIRONMENT DRAWING (环境绘制 / Desenho do Ambiente)
# ============================================================================

def draw_flat_mosaic_floor():
    """
    CN: 绘制平铺的马赛克地面。
    PT: Desenha o chão de mosaico ladrilhado.
    """
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_floor_id)
    set_material("stone")
    
    size = 150.0
    steps = 20
    step_size = (size * 2) / steps
    
    glNormal3f(0, 1, 0) 
    for i in range(steps):
        for j in range(steps):
            x1 = -size + i * step_size
            z1 = -size + j * step_size
            x2 = x1 + step_size
            z2 = z1 + step_size
            
            glBegin(GL_QUADS)
            glTexCoord2f(x1/2.0, z1/2.0)
            glVertex3f(x1, 0, z1)
            glTexCoord2f(x2/2.0, z1/2.0)
            glVertex3f(x2, 0, z1)
            glTexCoord2f(x2/2.0, z2/2.0)
            glVertex3f(x2, 0, z2)
            glTexCoord2f(x1/2.0, z2/2.0)
            glVertex3f(x1, 0, z2)
            glEnd()
    glDisable(GL_TEXTURE_2D)

def draw_obj_tree(x, z):
    """
    CN: 绘制一棵树（圆柱+圆锥）。
    PT: Desenha uma árvore (cilindro + cones).
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

def draw_obj_rock(x, z):
    """
    CN: 绘制岩石（十二面体）。
    PT: Desenha uma rocha (dodecaedro).
    """
    glPushMatrix()
    glTranslatef(x, 0.5, z)
    glRotatef(x * 10, 0, 1, 0)
    glRotatef(z * 10, 1, 0, 0)
    set_material("stone")
    glScalef(1.2, 0.8, 1.2)
    glutSolidDodecahedron()
    glPopMatrix()

def draw_garage_structure():
    """
    CN: 绘制车库结构（双层墙壁，防止漏光）。
    PT: Desenha a estrutura da garagem (paredes duplas para evitar vazamento de luz).
    """
    w, h, d, th = 8.0, 5.0, 10.0, 0.5
    
    # 1. Enable Culling to manage wall sides (开启面剔除 / Ativar Culling)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK) 

    # 2. Draw Exterior Walls (绘制外墙 / Paredes Externas)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_wall_id)
    set_material("stone")
    
    glBegin(GL_QUADS)
    # Back Wall
    glNormal3f(0,0,-1)
    glTexCoord2f(0,0)
    glVertex3f(w/2, 0, -d)
    glTexCoord2f(4,0)
    glVertex3f(-w/2, 0, -d)
    glTexCoord2f(4,2)
    glVertex3f(-w/2, h, -d)
    glTexCoord2f(0,2)
    glVertex3f(w/2, h, -d)
    # Left Wall
    glNormal3f(-1,0,0)
    glTexCoord2f(0,0)
    glVertex3f(-w/2, 0, -d)
    glTexCoord2f(4,0)
    glVertex3f(-w/2, 0, 0)
    glTexCoord2f(4,2)
    glVertex3f(-w/2, h, 0)
    glTexCoord2f(0,2)
    glVertex3f(-w/2, h, -d)
    # Right Wall
    glNormal3f(1,0,0)
    glTexCoord2f(0,0)
    glVertex3f(w/2, 0, 0)
    glTexCoord2f(4,0)
    glVertex3f(w/2, 0, -d)
    glTexCoord2f(4,2)
    glVertex3f(w/2, h, -d)
    glTexCoord2f(0,2)
    glVertex3f(w/2, h, 0)
    glEnd()
    glDisable(GL_TEXTURE_2D)

    # 3. Draw Interior Walls with Smart Lighting (绘制内墙 - 智能光照)
    set_material("garage_inner_wall")
    
    # ★ FIX: If car is OUTSIDE, disable car lights for inner walls
    # CN: 修复：如果车在外面，暂时关闭车灯，防止穿墙照亮内部
    # PT: Correção: Se o carro estiver fora, desative as luzes para evitar vazamento
    
    # Garage approximate bounds (车库大致范围): X[-4, 4], Z[-25, -15]
    is_car_inside = (-26 < car_pos[2] < -14) and (-5 < car_pos[0] < 5)
    
    if not is_car_inside:
        glDisable(GL_LIGHT2) # Left Headlight
        glDisable(GL_LIGHT3) # Right Headlight

    glBegin(GL_QUADS)
    # Back
    glNormal3f(0,0,1)
    glVertex3f(-w/2, 0, -d)
    glVertex3f(w/2, 0, -d)
    glVertex3f(w/2, h, -d)
    glVertex3f(-w/2, h, -d)
    # Left
    glNormal3f(1,0,0)
    glVertex3f(-w/2, 0, 0)
    glVertex3f(-w/2, 0, -d)
    glVertex3f(-w/2, h, -d)
    glVertex3f(-w/2, h, 0)
    # Right
    glNormal3f(-1,0,0)
    glVertex3f(w/2, 0, -d)
    glVertex3f(w/2, 0, 0)
    glVertex3f(w/2, h, 0)
    glVertex3f(w/2, h, -d)
    glEnd()

    # ★ Restore lights if they should be on (恢复车灯)
    if not is_car_inside and headlights_on:
        glEnable(GL_LIGHT2)
        glEnable(GL_LIGHT3)

    glDisable(GL_CULL_FACE)

    glDisable(GL_CULL_FACE) 

    # Roof & Door Animation (屋顶和车库门 / Telhado e Porta)
    glPushMatrix()
    glTranslatef(0, h, -d/2)
    glScalef(w+1, th, d+1)
    set_material("stone")
    glColor3f(0.3,0.3,0.3)
    glutSolidCube(1.0)
    glPopMatrix()
    
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
    CN: 绘制左侧的现代风格房子。
    PT: Desenha a casa moderna à esquerda.
    """
    glPushMatrix()
    glTranslatef(x, 0, z)
    
    # Main Body
    set_material("house_wall_white")
    glPushMatrix()
    glTranslatef(0, 2.0, 0)
    glScalef(6.0, 4.0, 6.0)
    glutSolidCube(1.0)
    glPopMatrix()
    
    # Upper Body
    glPushMatrix()
    glTranslatef(-1.5, 5.0, 0)
    glScalef(4.0, 2.0, 5.0)
    glutSolidCube(1.0)
    glPopMatrix()
    
    # Large Window
    set_material("house_window")
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    glVertex3f(-2.5, 3.5, 3.01)
    glVertex3f(2.5, 3.5, 3.01)
    glVertex3f(2.5, 0.1, 3.01)
    glVertex3f(-2.5, 0.1, 3.01)
    glEnd()
    glDisable(GL_BLEND)
    
    # Door
    set_material("wood")
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    glVertex3f(1.5, 2.2, 3.02)
    glVertex3f(2.5, 2.2, 3.02)
    glVertex3f(2.5, 0.1, 3.02)
    glVertex3f(1.5, 0.1, 3.02)
    glEnd()
    glPopMatrix()

def draw_classic_cottage(x, z):
    """
    CN: 绘制右侧的经典小屋。
    PT: Desenha o chalé clássico à direita.
    """
    glPushMatrix()
    glTranslatef(x, 0, z)
    w, h, d = 5.0, 3.0, 4.0
    
    # Walls
    set_material("house_wall_brick")
    glPushMatrix()
    glTranslatef(0, h/2, 0)
    glScalef(w, h, d)
    glutSolidCube(1.0)
    glPopMatrix()
    
    # Roof (Triangular)
    set_material("house_roof_dark")
    h_roof = 2.0
    overhang = 0.4
    glBegin(GL_TRIANGLES)
    glNormal3f(0,0,1)
    glVertex3f(-w/2,h,d/2)
    glVertex3f(w/2,h,d/2)
    glVertex3f(0,h+h_roof,d/2)
    glNormal3f(0,0,-1)
    glVertex3f(0,h+h_roof,-d/2)
    glVertex3f(w/2,h,-d/2)
    glVertex3f(-w/2,h,-d/2)
    glEnd()
    
    glBegin(GL_QUADS)
    # Left Slope
    glNormal3f(-h_roof, w/2, 0)
    glVertex3f(-w/2-overhang, h-0.2, d/2+overhang)
    glVertex3f(0, h+h_roof, d/2+overhang)
    glVertex3f(0, h+h_roof, -d/2-overhang)
    glVertex3f(-w/2-overhang, h-0.2, -d/2-overhang)
    # Right Slope
    glNormal3f(h_roof, w/2, 0)
    glVertex3f(0, h+h_roof, d/2+overhang)
    glVertex3f(w/2+overhang, h-0.2, d/2+overhang)
    glVertex3f(w/2+overhang, h-0.2, -d/2-overhang)
    glVertex3f(0, h+h_roof, -d/2-overhang)
    glEnd()
    
    # Door and Windows
    set_material("wood")
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    glVertex3f(-0.5, 2.0, d/2+0.01)
    glVertex3f(0.5, 2.0, d/2+0.01)
    glVertex3f(0.5, 0.0, d/2+0.01)
    glVertex3f(-0.5, 0.0, d/2+0.01)
    glEnd()
    
    set_material("house_window")
    glBegin(GL_QUADS)
    glNormal3f(0, 0, 1)
    glVertex3f(-1.8, 2.0, d/2+0.01)
    glVertex3f(-1.0, 2.0, d/2+0.01)
    glVertex3f(-1.0, 1.0, d/2+0.01)
    glVertex3f(-1.8, 1.0, d/2+0.01)
    glVertex3f(1.0, 2.0, d/2+0.01)
    glVertex3f(1.8, 2.0, d/2+0.01)
    glVertex3f(1.8, 1.0, d/2+0.01)
    glVertex3f(1.0, 1.0, d/2+0.01)
    glEnd()
    glPopMatrix()

# ============================================================================
# 5. CAR COMPONENT DRAWING (车辆组件绘制 / Desenho dos Componentes do Carro)
# ============================================================================

def draw_wheel(radius, width):
    """
    CN: 绘制车轮。
    PT: Desenha a roda.
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

def draw_detailed_steering_wheel():
    """
    CN: 绘制方向盘。
    PT: Desenha o volante.
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
    CN: 绘制座椅。
    PT: Desenha o banco.
    """
    set_material("car_seat")
    # Base (坐垫)
    glPushMatrix()
    glScalef(0.5, 0.15, 0.6)
    glutSolidCube(1.0)
    glPopMatrix()
    # Back (靠背)
    glPushMatrix()
    glTranslatef(0, 0.4, 0.25)
    glRotatef(-10, 1, 0, 0)
    glScalef(0.5, 0.7, 0.1)
    glutSolidCube(1.0)
    glPopMatrix()
    # Headrest (头枕)
    glPushMatrix()
    glTranslatef(0, 0.8, 0.3)
    glScalef(0.3, 0.2, 0.1)
    glutSolidCube(1.0)
    glPopMatrix()

def draw_front_body():
    """
    CN: 绘制车头（分段绘制以实现平滑的高光反光）。
    PT: Desenha a frente do carro (segmentada para reflexos suaves).
    """
    set_material("car_paint_metal")
    profile = [(-2.4, 0.1), (-2.4, 0.4), (-2.0, 0.55), (-0.9, 0.65)]
    w_body = 0.95
    
    # Left Half (左半部分)
    glBegin(GL_QUAD_STRIP)
    for z, y in profile:
        # Normal tilts left (法线向左倾斜)
        glNormal3f(-0.7, 0.5, 0.0)
        glVertex3f(-w_body, y, z)
        # Normal straight up (法线垂直向上，产生高光)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, y, z)
    glEnd()
    
    # Right Half (右半部分)
    glBegin(GL_QUAD_STRIP)
    for z, y in profile:
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, y, z)
        # Normal tilts right (法线向右倾斜)
        glNormal3f(0.7, 0.5, 0.0)
        glVertex3f(w_body, y, z)
    glEnd()
    
    # Side Cap (侧面封口)
    for side in [-1, 1]:
        glBegin(GL_POLYGON)
        glNormal3f(side, 0, 0)
        for z, y in profile:
            glVertex3f(side * w_body, y, z)
        glVertex3f(side * w_body, 0.1, -0.9)
        glVertex3f(side * w_body, 0.1, -2.4)
        glEnd()
    
    # Inner Cover (仪表台封盖)
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
    CN: 绘制车尾（同样分段以增强金属质感）。
    PT: Desenha a traseira do carro (segmentada para efeito metálico).
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
    CN: 绘制后翼子板（连接车门与车尾）。
    PT: Desenha o para-lama traseiro.
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
    """ CN: 绘制底盘。 PT: Desenha o chassi. """
    set_material("car_inner_black")
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glVertex3f(-0.95, 0.1, 1.4); glVertex3f(0.95, 0.1, 1.4)
    glVertex3f(0.95, 0.1, -0.9); glVertex3f(-0.95, 0.1, -0.9)
    glEnd()

def draw_door_object(side):
    """ CN: 绘制车门。 PT: Desenha a porta. """
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
    """ CN: 绘制玻璃座舱。 PT: Desenha a cabine de vidro. """
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

def draw_car():
    """ CN: 组装整个车辆。 PT: Monta o carro inteiro. """
    glPushMatrix()
    glTranslatef(car_pos[0], 0.35, car_pos[2])
    glRotatef(math.degrees(car_yaw), 0, 1, 0)
    
    draw_front_body()
    draw_rear_body()
    draw_rear_fender()
    draw_chassis_floor()

    # Doors (车门)
    door_hinge_z = -0.9
    door_width_offset = 0.95
    glPushMatrix()
    glTranslatef(-door_width_offset, 0, door_hinge_z)
    if car_door_open: glRotatef(-60, 0, 1, 0)
    draw_door_object(-1)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(door_width_offset, 0, door_hinge_z)
    if car_door_open: glRotatef(60, 0, 1, 0)
    draw_door_object(1)
    glPopMatrix()

    # Spoiler (扰流板)
    set_material("car_inner_black")
    glPushMatrix()
    glTranslatef(0, 0.75, 1.9)
    glPushMatrix()
    glTranslatef(-0.5, 0, 0)
    glScalef(0.1, 0.3, 0.2)
    glutSolidCube(1.0)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.5, 0, 0)
    glScalef(0.1, 0.3, 0.2)
    glutSolidCube(1.0)
    glPopMatrix()
    glTranslatef(0, 0.15, 0)
    glPushMatrix()
    glScalef(2.2, 0.1, 0.5)
    glutSolidSphere(0.5, 20, 10)
    glPopMatrix()
    glPopMatrix()

    # Mirrors (后视镜)
    set_material("car_paint_metal")
    for s in [-1, 1]:
        glPushMatrix()
        glTranslatef(s * 0.9, 0.8, -0.7)
        glRotatef(s * -15, 0, 1, 0)
        glScalef(0.25, 0.15, 0.15)
        glutSolidSphere(1.0, 10, 10)
        glPopMatrix()

    # Lights (车灯)
    if headlights_on:
        glEnable(GL_LIGHT2)
        glLightfv(GL_LIGHT2, GL_POSITION, [-0.6, 0.0, -2.0, 1.0])
        glLightfv(GL_LIGHT2, GL_SPOT_DIRECTION, [0.0, -0.2, -1.0])
        glEnable(GL_LIGHT3)
        glLightfv(GL_LIGHT3, GL_POSITION, [0.6, 0.0, -2.0, 1.0])
        glLightfv(GL_LIGHT3, GL_SPOT_DIRECTION, [0.0, -0.2, -1.0])
        glMaterialfv(GL_FRONT, GL_EMISSION, [1.0, 1.0, 0.9, 1.0])
        glColor3f(1.0, 1.0, 0.9)
    else: 
        glDisable(GL_LIGHT2)
        glDisable(GL_LIGHT3)
        glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])
        set_material("light_bulb_off")
        
    glPushMatrix()
    glTranslatef(-0.7, 0.3, -2.35)
    glScalef(0.25, 0.1, 0.1)
    glutSolidSphere(0.8, 10, 10)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.7, 0.3, -2.35)
    glScalef(0.25, 0.1, 0.1)
    glutSolidSphere(0.8, 10, 10)
    glPopMatrix()
    
    if headlights_on:
        glMaterialfv(GL_FRONT, GL_EMISSION, [1.0, 0.0, 0.0, 1.0])
        glColor3f(1.0, 0.0, 0.0)
    else:
        glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])
        set_material("tail_light_off")
        
    glPushMatrix()
    glTranslatef(-0.6, 0.5, 2.1)
    glScalef(0.3, 0.1, 0.05)
    glutSolidCube(1.0)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.6, 0.5, 2.1)
    glScalef(0.3, 0.1, 0.05)
    glutSolidCube(1.0)
    glPopMatrix()
    glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])


    set_material("car_inner_black") 
    glPushMatrix()
    # 位置：X居中, Y=0.4(高度), Z=0.55(刚好在座椅靠背后面)
    glTranslatef(0.0, 0.4, 0.75) 
    # 大小：X=1.7(够宽), Y=0.7(够高挡住后面), Z=0.05(薄板)
    glScalef(1.8, 0.4, 0.05)
    glutSolidCube(1.0)
    glPopMatrix()

    # Seats (座椅)
    glPushMatrix()
    glTranslatef(-0.45, 0.1, 0.35)
    draw_seat()
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0.45, 0.1, 0.35)
    draw_seat()
    glPopMatrix()

    # Steering Wheel (方向盘)
    glPushMatrix()
    glTranslatef(-0.45, 0.55, -0.50)
    glRotatef(20, 1, 0, 0)
    glRotatef(steering_angle * 1.5, 0, 0, 1)
    draw_detailed_steering_wheel()
    glPopMatrix()

    # Wheels (车轮)
    for s in [-1, 1]: 
        glPushMatrix()
        glTranslatef(s*1.0, 0.0, -1.3)
        glRotatef(steering_angle, 0, 1, 0)
        glRotatef(-wheel_rotation, 1, 0, 0)
        glRotatef(90, 0, 1, 0)
        draw_wheel(0.33, 0.25)
        glPopMatrix()
        
    rot_rear = wheel_rotation * (0.33/0.55)
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
# 6. LOGIC & CONTROL (逻辑与控制 / Lógica e Controle)
# ============================================================================

def set_projection():
    """ CN: 设置投影矩阵。 PT: Configura a matriz de projeção. """
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    target_fov = 65.0 if camera_mode == 2 else 45.0
    gluPerspective(target_fov, 800/600, 0.1, 300.0)
    glMatrixMode(GL_MODELVIEW)

def draw_scene():
    """ CN: 主渲染函数。 PT: Função principal de renderização. """
    set_projection()
    
    if is_night:
        glClearColor(0.05, 0.05, 0.1, 1.0)
    else:
        glClearColor(0.6, 0.8, 1.0, 1.0)
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    # Camera Logic
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
    
    # Lights
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
    draw_flat_mosaic_floor()
    
    random.seed(123)
    for _ in range(15):
        px, pz = random.randint(-40, 40), random.randint(-40, 40)
        if abs(px) > 8 or abs(pz) > 8: draw_obj_tree(px, pz)
    for _ in range(10):
        px, pz = random.randint(-30, 30), random.randint(-30, 30)
        if abs(px) > 8 or abs(pz) > 8: draw_obj_rock(px, pz)
    
    glPushMatrix()
    glTranslatef(0, 0, -15)
    draw_garage_structure()
    glPopMatrix()
    
    draw_modern_house(-15, -10)
    draw_classic_cottage(15, -10)
    
    draw_car()
    glutSwapBuffers()

def update(v):
    global car_door_angle
    target_angle = 60.0 if car_door_open else 0.0
    car_door_angle += (target_angle - car_door_angle) * 0.1
    glutPostRedisplay()
    glutTimerFunc(16, update, 0) 

def special_keys(k, x, y):
    global car_pos, car_yaw, wheel_rotation, steering_angle
    if k == GLUT_KEY_LEFT:
        steering_angle = min(steering_angle + STEER_SPEED, MAX_STEER)
    elif k == GLUT_KEY_RIGHT:
        steering_angle = max(steering_angle - STEER_SPEED, -MAX_STEER)
    
    move_dir = 0
    if k == GLUT_KEY_UP:
        move_dir = 1
        wheel_rotation += 15 
    elif k == GLUT_KEY_DOWN:
        move_dir = -1
        wheel_rotation -= 15 
        
    if move_dir != 0:
        car_pos[0] -= move_dir * MOVE_SPEED * math.sin(car_yaw)
        car_pos[2] -= move_dir * MOVE_SPEED * math.cos(car_yaw)
        car_yaw += move_dir * (MOVE_SPEED / WHEELBASE) * math.tan(math.radians(steering_angle))

def keyboard(key, x, y):
    global car_door_open, garage_door_height, cam_yaw, cam_pitch, camera_mode, steering_angle, is_night, headlights_on
    k = key.decode("utf-8").lower()
    
    if k=='o': car_door_open = not car_door_open 
    if k=='g': garage_door_height = min(garage_door_height + 0.1, 5.0) 
    if k=='f': garage_door_height = max(garage_door_height - 0.1, 0.0) 
    if k=='v':
        camera_mode = (camera_mode + 1) % 3
        cam_yaw = 0.0
        cam_pitch = 0.4
    if k==' ': steering_angle = 0.0 
    if k=='n': is_night = not is_night 
    if k=='h': headlights_on = not headlights_on 
    if k=='\x1b': sys.exit() 

def mouse_func(button, state, x, y):
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
    """ CN: 初始化OpenGL设置。 PT: Inicializa configurações OpenGL. """
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
    
    glLightf(GL_LIGHT2, GL_SPOT_CUTOFF, 30.0)
    glLightfv(GL_LIGHT2, GL_DIFFUSE, [1.0, 1.0, 0.8, 1.0])
    glLightf(GL_LIGHT3, GL_SPOT_CUTOFF, 30.0)
    glLightfv(GL_LIGHT3, GL_DIFFUSE, [1.0, 1.0, 0.8, 1.0])
    
    init_resources()

if __name__ == "__main__":
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutCreateWindow(b"Final Project - Ultimate Optimized")
    
    init()
    
    glutDisplayFunc(draw_scene)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutMouseFunc(mouse_func)
    glutMotionFunc(motion_func)
    glutReshapeFunc(lambda w,h: glViewport(0,0,w,h)) 
    glutTimerFunc(16, update, 0)
    
    # --- Terminal Instructions (CN/PT) ---
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