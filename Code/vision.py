# -*- coding: utf-8 -*-
"""
Created on Mon Feb 26 17:19:59 2018

@author: James Wu
"""

import cv2
import numpy as np
import time
import random
import os
import serial
import struct


#==============================================================================
#   1.定义一些零碎的函数
#==============================================================================
# 开操作（精）
def opening_3v3(src):
    kernel = np.ones((3,3), np.uint8)
    dst = cv2.morphologyEx(src, cv2.MORPH_OPEN, kernel)
    return dst

# 开操作（粗）
def opening_5v5(src):
    kernel = np.ones((5,5), np.uint8)
    dst = cv2.morphologyEx(src, cv2.MORPH_OPEN, kernel)
    return dst

# 闭操作（竖向为主）
def closing_12v6(src):
    kernel = np.ones((12,6), np.uint8)
    dst = cv2.morphologyEx(src, cv2.MORPH_CLOSE, kernel)
    return dst

# 闭操作（精）
def closing_5v5(src):
    kernel = np.ones((5,5), np.uint8)
    dst = cv2.morphologyEx(src, cv2.MORPH_CLOSE, kernel)
    return dst


#==============================================================================
#   2.找i先生(小人)函数 
#       输入：图像
#       输出：小人的底部中点横坐标、小人的宽度
#==============================================================================
def iDetection(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)    # 将原图像从rgb颜色空间映射到hsv颜色空间
    
    lower_purple = np.array([105,35,50])    # 其中的35不能再小了，否则阴井盖会假阳性
    upper_purple = np.array([135,150,130])
    
    mask_i = cv2.inRange(hsv, lower_purple, upper_purple)   # 颜色分割，阈值化，得到小人的掩膜
 
    mask_i = opening_3v3(mask_i)    # 开操作
    mask_i = closing_12v6(mask_i)   # 闭操作：竖向分量要大一些，才能将小人的头和身体合并(注意np和cv2的横竖是反的)
    
    contours= cv2.findContours(mask_i, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[1]   # 提取轮廓
    # 注：findContours返回值有三：image, contours, hierarchy, 这里取第二个，即图像中所有contours的一个python list.
    # 文档解释：Each individual contour is a Numpy array of (x,y) coordinates of boundary points of the object.
    
    # 找面积最大的contours，并作最小包围矩形
    if len(contours)>0:    
        max_contour = max(contours, key=cv2.contourArea) 
    
        rectangle = cv2.boundingRect(max_contour)   # 得到最小包围矩形信息
        x,y,w,h = rectangle
        
        rectangle_pts = np.array([[x,y],[x+w,y],[x+w,y+h],[x,y+h]], np.int32)   # 最小包围矩形各顶点
        cv2.polylines(frame, [rectangle_pts], True, (0,255,0), 3) # 绘制最小包围矩形
    
        x_i = x+w//2
        y_i = y+h
        center_pt=(x_i,y_i)   # 小人底部中点坐标
        cv2.circle(frame, center_pt, 8, (0,0,255), -1)   # 绘制小人底部中点——参考点A
        
        # 输出起点横坐标
        print('i先生的横坐标：')
        print(x_i)
        print('i先生的宽度：')
        print(w)
  
    cv2.imshow('mask_i',mask_i)         # 图像分割结果
    cv2.imshow('i_detected', frame)     # 找i先生结果
    return x_i, w


#==============================================================================
#   3.找目标点函数
#       输入：图像、小人的底部中点横坐标、小人的宽度
#       输出：目标点横坐标
#==============================================================================
def targetDetection(frame, x_i, w):
    #==========================================================================
    #   根据i先生的位置确定感兴趣区域：ROI
    #==========================================================================
    if(x_i <= frame.shape[1]//2):
        L = x_i + w//2
        R = frame.shape[1]
    else:
        L = 0
        R = x_i - w//2
    T = int(frame.shape[0]*0.3)
    B = int(frame.shape[0]*0.7)
    ROI = frame[T:B, L:R]   # 注意python里面是先竖后横！
    
    ROI = cv2.GaussianBlur(ROI,(3,3),0)  # 高斯滤波，模糊化处理
    
    #==========================================================================
    #   处理hsv图像，分通道分别canny然后使用逻辑或融合
    #==========================================================================
    hsv = cv2.cvtColor(ROI, cv2.COLOR_BGR2HSV)      # 转hsv图像
    (h,s,v) = cv2.split(hsv)                        # hsv彩色通道分离
    
    edges_h = cv2.Canny(h, 20, 40)                  # 三通道分别canny边缘检测
    edges_s = cv2.Canny(s, 20, 40) 
    edges_v = cv2.Canny(v, 20, 40) 
    edges = cv2.bitwise_or(edges_h,edges_s)         # 逻辑或，将三个通道的结果融合
    edges = cv2.bitwise_or(edges,edges_v)
              
    edges = closing_5v5(edges)                      #闭操作：连接断线(主要是顶点)
    
    #==========================================================================
    #   找到目标最顶点的坐标(此算法参考了知乎用户“皮皮哇”的实现)
    #==========================================================================
    y_target = 0   # 初始化目标最顶点的纵坐标
    for row in edges[0:]:   # 遍历行
        if max(row):        # 如果存在最大值即说明有白点，跳出循环得到最高点所在行数
            break
        y_target += 1
        
    x_target = int(np.mean(np.nonzero(edges[y_target])))    # 取均值，解决该行有多个点的bug
    
    x_target += L   #回归原图像坐标
    y_target += T
    
    target_pt = (x_target,y_target)
    cv2.circle(frame, target_pt, 8, (0,0,255), -1)  # 在原图像用红点标注最高点
    
    #==========================================================================
    #   输出结果
    #==========================================================================
    print('目标最高点的横坐标：')
    print(x_target)
    
    cv2.imshow('edges',edges)                       # 边缘：hsv融合结果
    cv2.imshow('target_detected', frame)            # 找目标结果
    
    return x_target


#==============================================================================
#   4.串口通信函数
#       输入：串口、数据
#       输出：无
#==============================================================================
def serial_send(Serial, data):
    Serial.write(struct.pack('H',data)) # 将待传数据以16进制码形式打包，并发送到串口


#==============================================================================
#   5.蓄力一跳函数
#       输入：距离
#       输出：无
#       效果：计算按压时间，并将按压时间通过串口发送给单片机
#==============================================================================
def jump(distance):
    press_time = distance * 2.5             # 距离乘上参数得到按压时间，该参数需调试！
    press_time = max(press_time, 200)       # 设置 200 ms 是最小的按压时间
    press_time = int(press_time)
    print('按压时间（ms）为：')
    print(press_time)
    serial_send(ser, press_time)
    time.sleep(press_time / 1000.0)         # 操作完毕后系统暂停一会，以保证拿到附加分
    
              
#==============================================================================
#   6.adb方法传递截屏函数
#==============================================================================
def pullScreenshot():
    os.system('adb shell screencap -p /sdcard/wechat_jump.png') # 手机截屏
    os.system('adb pull /sdcard/wechat_jump.png')   # 将截屏pull到上位机来


#==============================================================================
#   **************************主函数入口***********************************
#==============================================================================
# 设置串口参数
ser = serial.Serial()
ser.baudrate = 9600    # 设置比特率为9600bps
ser.port = 'COM4'      # 单片机接在哪个串口，就写哪个串口。这里默认接在"COM4"端口
ser.open()             # 打开串口

# 进入主循环
while True:
    pullScreenshot()   # 手机实时截屏并上传至上位机

    frame = cv2.imread('.\wechat_jump.png')
    frame=cv2.resize(frame,(720,1280))  # 重设截屏图像大小
    
                    
    frame1 = frame.copy()
    frame2 = frame.copy()
    x_i, w = iDetection(frame1)                 # 找i先生(小人)
    x_target = targetDetection(frame2, x_i, w)  # 找目标点
    
    # 计算横向距离
    dist = np.abs(x_i - x_target)
    print('横向距离为：')
    print(dist)
    
    jump(dist)                                  # 蓄力一跳
    time.sleep(random.uniform(1.5,2.0))         # 系统暂停1.5-2.0秒，引入随机因子
    
    k = cv2.waitKey(10) & 0xFF
    if k==27:   #按“Esc”退出
        break

ser.close()                                     # 关闭串口
cv2.destroyAllWindows()                         # 关闭所有串口
