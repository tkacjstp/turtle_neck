r"""
========================================================================
 �źϸ� �Ǻ��� (posture.py)   ���: ������ - ���� / �������ڼ� ���
========================================================================

[�� ���α׷��� �ϴ� ��]
  ���� ��ķ���� �󱼰� ����� ã��, ó���� �� ����� "�ٸ� �ڼ�"�� "�źϸ� �ڼ�"��
  ���� ���� �޶�� �ؼ� �н��� ��, ���� �ڼ��� �� �� ��� ������� ����(%)�� �����Ѵ�.
  ��ǰ ���ÿ����� �������� �ٲ�� �ڵ����� ���� �н��ϰ�, ���ϰ� �������� �ٷ� �����Ѵ�.

  ��ķ -> �ڼ� �н�(�ٸ� �ڼ� 3�� + �źϸ� 3��) -> �ǽð� ���� -> ����/���/����
       -> 3�ʸ���(���°� �ٲ�� �ٷ�) ������ ���� -> �� ������(http://����IP:5050)���� ��� Ȯ��


[�Ǻ� ���]  ����� ��(�Ǵ� ��Ʈ��) ��ķ 1���� ���鿡�� ����
  1) �� ��ġ�� 3D�� ���
     Face Mesh(�� 468��) �� ǥ���� �ٲ� �� �����̴� 33��(���� �������롤�̸�)��
     MediaPipe ǥ�� �� 3D ������ ���缭(solvePnP) �Ӹ��� 3D ��ġ�� ���ϰ�, ���� "��" ��ġ�� ��.
     -> �ڰ� �ƴ϶� �͸� ���Ƿ� ������ ���̰ų� �����̴� ��(Ű���� ���� ��) ���� ���� ����
  2) ���� ������ ���� (���� �߿�)
     ���(Pose)�� 3D ��ġ�� ����: ����� ī�޶� ��������� �а� ���̴� ������ �յ� �Ÿ���,
     ȭ�� �� ���̷� ���Ʒ��� ���.
     �������� ������ ���� ���̸�(ô�� �߸�) ������-���-�Ͱ� �� ����ó�� ���� ���Ƽ�,
     �ʹ� ����� ������ ��ŭ�� (����+��)/���� ��(�� 1.3��)��ŭ ������ -> �׸�ŭ�� ����
     "�� ������ ���� �Ÿ�(cm)"�� ����. �̰� �źϸ�.
     -> �������� ���̱�, �ڷ� ����, ����° �ٰ�����, �� ��Ʋ��, ��� ������ �źϸ����� �� ��
        (����� �־��� ���� ���� ȭ�� �� ���̵� ���� �ö󰡾� '�ڷ� ���'���� ����. ���� �״�θ� ��Ʋ��)
     -> ���� ���¿��� ����� ���� �װ� �źϸ����� ����
  3) ���� ���� �н�: �ٸ� �ڼ� 3�� + �źϸ� 3�ʸ� ���� �ָ�, �źϸ��� �� ���� ���� ��������
     �����Ρ��Ʒ��� �� cm �����̴��� �н�. ���� = ���� �� �������� �� ���⿡ ���� ����
     (�ٸ� �ڼ� 0%, �н��� �źϸ� 100%, ȭ�顤������ 0~100%�� ����)
     10% �̻��̸� �ٷ� ���, 20% �̻��� ���°� 2.5��(danger_after_sec) �̾����� ����
  4) ���� ���: Pose�� ��� ���� ���� ���� �ö󰡼� �� ���� -> ���� ��� ������ ����� ����ؼ� ���(10��)
     ������ ���� ���� ��� ���� �� ���̸�: 3�� ���� ������ ���� ����
     ����� ȭ�� ������ ������: ���� �������� �� �� ��� �������� ���� ("MOVE BACK")
  5) �� ����� ���󰡱�: ó�� ���� ���(���� ũ�� ���̴� ��)�� ��� ����. ���� �߿� �ٸ� �����
     ȭ�鿡 ���͵� �����ϰ�, ����� �� ��� �ֺ��� �߶� ���. 5�� �Ѱ� �� ���̸� ���� ����� ���� ���
     ���� �н�

  ���� ������ ���� ó�� (���ÿ�)
  - ����� ��ٸ��� �ʰ� �ٷ� ǥ�� (�ڼ��� �ٲ�� �� 0.3�� �ȿ� �ݿ�)
  - �Ϳ� ��� �������� �Ȱ��� ������� �ε巴�� ��: ������ ���� 0.25��(smooth_sec), ������ ���� ����
    0.6�ʷ� �� �ε巴�� (���� �Ȱ��� �ʾ����� ���� �������� ���� ��߳��� ����)
  - ������ �ֱ� 3���� ��� ��(�� �� Ƣ�� �� ����) -> One Euro ����
  - ��(�ʴ� 30��)�� ���(�ʴ� 5��)�� ��� �ӵ��� �޶�, ������ ���� "���� ȭ��"���� ����
    �󱼰� ����� ¦���� �� (�� �׷��� ���� ���� �� �͸� ���� ������ ��ó�� ���� ���� ����)
  - ����� �� �ڿ��� ������ 3%(hysteresis_pct) ���� ��迡�� �������� �ʰ� ��
  - �ڸ��� ������ 1�� �ȿ� ��������, 5�� �̻� ��� ���� �������� ���� �н��� ó������

  ���ϸ� ���̱� ���� ó�� (��������̿�, ������ 4���� ����)
  - ī�޶� ������ : ī�޶� �б⸸ ��(camera_fps, �⺻ 30fps). �׻� "���� �ֱ� ȭ��" �ϳ��� ����
  - �� ������   : Face Mesh(��)�� ���, �ʴ� analysis_fps��
  - ��� ������   : Pose(���)�� ���, �ʴ� pose_fps�� (���� ���ſ� ���. ����� õõ�� �������� ���)
  - ���� ������   : ȭ�� ǥ��(ī�޶� �ӵ� �״��) + ����(�� ��� ����� ���� ������, ��귮 ���� ����)
  -> MediaPipe�� ����ϴ� ���� ���̽� ���(GIL)�� Ǯ�� �༭, �󱼡���� ����� �����������
     ���� �ٸ� CPU �ھ�� ���ÿ� ��. ���ſ� ����� �ʾ����� ȭ���� ������ ����
  - ������ Ƚ���� ����ϰ� ���� �ð��� ��� CPU�� �� ���� ���� (���� ����� ���� app.py�� ���� �ְ�)
  - ȭ�� ������ �Ʒ��� cam/screen/face/pose �ʴ� ó�� Ƚ��(fps) ǥ��, �α׿��� 10�ʸ��� ���
  �� ��������� ��õ ����: "analysis_fps": 15, "pose_fps": 5, "model_complexity": 0
  �� ��ķ 60fps: ��ķ�� 60fps�� �����ؾ� �ϰ�(��κ� MJPG ��Ŀ�����), ������ ��ƾ� ��
     (��ο�� ��ķ�� ������ ���� �ð��� �÷��� 15~30fps�� ������). ���� ���� �α׷� Ȯ��


[�ʿ� ȯ��]  �� ������ �ٸ��� ��ġ�� �� �ǰų� ���� �� ������ ��
  Python    : 3.9 ~ 3.12 (3.11 ����)
              - mediapipe 0.10.18�� 3.9~3.12�� ����. 3.13 �̻�, 3.8 ���ϴ� ��ġ �Ұ�
              - ��������� OS Bookworm�� �⺻�� 3.11�̶� �״�� ��� ����
              - 3.13 �̻��̸� 3.11�� ���� ��ġ�ؼ� ����ȯ���� ���� ��
              - ���� Ȯ��: python3 --version (������� py --version)
  mediapipe : 0.10.18 (���� ��� �� �������� ����)
              - �� �ڵ�� ���� ����� mp.solutions.pose �� �����
              - mp.solutions �� 0.10.30 �̻�(�ֽ� 1.x ����)���� ������
                -> ���� ���� ���� ��ġ�ϸ� "has no attribute 'solutions'" ������ ���� �� ��
              - 0.10.20, 0.10.21�� ���������(ARM 64��Ʈ)�� ��ġ ������ ����
                -> ��������̿����� ��ġ�Ǵ� ������ ������ 0.10.18
  OpenCV    : mediapipe ��ġ �� opencv-contrib-python �� �Բ� ��ġ�� (���� ��ġ ���ʿ�)
              - opencv-python �� ���� ��ġ�ϸ� OpenCV�� �� ���� �浹�� �� ����
              - opencv-python-headless �� ��ġ�� ������ ī�޶� â�� �� �� -> ������ ��
  numpy     : mediapipe ��ġ �� 1.x ������ �Բ� ��ġ�� (numpy 2.x �� ȣȯ �� ��)
  ���      : ��ķ �ʼ� (����ũ�� PC�� USB ��ķ�� �Ⱦƾ� ��)
              ��������̴� 64��Ʈ OS �ʿ�


[��ġ]  ó�� �� ����. turtle_neck ���� �ȿ��� ����
  ������ (���� ������Ʈ cmd ���, PowerShell ����)
      py -3.11 -m venv venv
      venv\Scripts\python -m pip install flask mediapipe==0.10.18
  �� / ���������
      python3.11 -m venv venv
      source venv/bin/activate
      pip install flask mediapipe==0.10.18
  ��ġ Ȯ��: �׽�Ʈ ���� �� �������� OK�� ������ ����
      ������: venv\Scripts\python test_posture.py     ��/���������: python test_posture.py


[���� �� üũ����Ʈ]  �ϳ��� �� �Ǹ� ����� �������� ����
  �� ����(app.py)�� ���� �״°�?  (�Ǻ��⺸�� ����, â�� ���� ���� �� �� ��)
  �� config.json�� server_url�� �´°�?
      - �� ��ǻ�� �ϳ��� �׽�Ʈ�� �� : "http://127.0.0.1:5050/api/record"
      - ������ �ٸ� ��ǻ���� ��      : "http://������ǻ��IP:5050/api/record"
        (�� ��ǻ�Ͱ� ���� ��������/��Ʈ��ũ�� �־�� ��)
  �� config.json�� ��ĥ �� ���ڸ� �ٲ�°�? (��ǥ������ǥ�� �ǵ帮�� ���� �� ��)
  �� ��ķ�� ����Ǿ� �ְ�, �ٸ� ���α׷�(��, ī�޶� �� ��)�� ���� ���� ������?
  �� ��ķ�� ����� �� ����� �ΰ�, ȭ�鿡 �󱼰� ���� ���(���� ���ʱ���)�� ���̴°�?
      ����� �� ���̸� ���� �������� �� ���� ���� ���̸� �źϸ����� ���� �� ����
  �� config.json�� camera_tilt_deg�� ��ķ�� �Ʒ��� ������ ������ ����Ѱ�?
      (����� ������ ����� �����ٺ��� ���� 10~15, ��Ʈ�� ȭ�� ��ķ�̸� 0~5. ���� ������ ��)
  �� ���� ��� ���̴°�? (�ڿ� â���� �־� �����̸� �� �ν��� �� �� ��)
  �� ī�޶� ����(ȭ�� ��)�� �ٸ� ��� ���� ũ�� ������ �ʴ°�? (�����忡���� ��� �� ����)


[����]
  ������: venv\Scripts\python posture.py      ��/���������: python posture.py
  ����  : ī�޶� â���� q Ű, �Ǵ� ���� â���� Ctrl+C
  �ٽ� �н� : ī�޶� â���� c Ű

  ������ ���� ���� (ȭ�鿡 ����� �ȳ��� ����)
  1) ī�޶� �տ� ������ �ڵ� ����
  2) "1/2 SIT UP STRAIGHT 3,2,1" -> �ٸ��� �ɾƼ� 3�� ���� ("HOLD STRAIGHT...")
  3) "2/2 NOW TURTLE NECK! 3,2,1" -> ��� ���� �ڼ�ó�� �Ӹ��� ������ ���� 3�� ���� ("HOLD IT...")
     -> ȭ�鿡 "head forward +O.Ocm"�� ���� ������ ���� �Ÿ��� �ǽð����� ���� (2cm �̻��̸� ���)
     -> ��κ� �� ���� ����. �ٸ� �ڼ� �ܰ�� �ٽ� ���� ����
     -> ������ �ʹ� ũ��(���� 1.5cm�� �� �������ų� ���� ��鸲) "One more time ..."�� �߰� 3)�� �� �� ���� �� ��
     -> �� ��°�� �����ϸ� �� �ݺ����� �ʰ�, �źϸ��� �⺻��(�� �� 5cm, �Ʒ� 2cm)���� �н��ؼ� �ٷ� ���� ����
     -> �н� �� ���(3�� �̳�) ���� �� ���̸� ������ ����ٰ� �̾ ��
  4) ���� �ǽð� ����. ȭ�� �Ʒ� ���밡 ����, �� �� �� ���� ���(10)������(20) ����
  5) �ڸ��� ���� 5�ʰ� ������ ���� ����� ���� 1)���� �ٽ�

  �� ���ο����� �� ��: config.json�� new_person_reset_sec�� 0���� �ϸ�
     �н� ����� baseline.json�� ������ �ΰ� ���� ���࿡�� �״�� ���
  �� ����� �ƿ� �� ������ config.json�� "use_shoulders": false (�󱼸����� ����)


[ī�޶� â ���� ��]  (OpenCV�� �ѱ��� �� �Ἥ ����� ǥ��)
  NO PERSON           : ����� �� ����
  FACE NOT FOUND      : �� �ν� �� �� -> ���� ����, ���� Ȯ�� (����ũ�������� ������ �� ��)
  TURN TO CAMERA      : ������ ������ ����(35�� �̻�) ���� -> ���� ����
  MOVE BACK - show both shoulders : ����� ȭ�� �� -> �ڷ� �������ų� ī�޶� ���� ����
  LOWER YOUR ARMS     : ���� 10�� �Ѱ� ��� �־ ��� ��ġ�� �� �� ���� -> �� ������
  FACE THE CAMERA     : ���� ũ�� ��ư ���°� 10�� �Ѱ� �̾��� -> ī�޶� ������ �ɱ�
  face hidden - keeping last result : ���� ���̴µ� ���� ������(�� ��) -> 3�� ���� ������ ���� ����
                        �� ������ �� ���� ���°� 1��(�󱼸� ���������� 3��) �Ѱ� �̾����� ���¸� �������� ����
  1/2 ..., 2/2 ...    : �ڼ� �н� �� (�� [����] ���� ����)
  NORMAL  (�ʷ�)      : ����
  WARNING (��Ȳ)      : ��� - ���� 10%(warning_pct) �̻� (�ٷ� ǥ��)
  DANGER  (����)      : ���� - ���� 20%(danger_pct) �̻��� 2.5��(danger_after_sec) �̻� �̾���
  �� ���� 0% = �н��� �ٸ� �ڼ�, 100% = �н��� �źϸ� �ڼ� (0~100%�� ����)
  �� �ϴû� �� = �ڡ��� ������, �� �� = �������, ��� �� = ��(����)~��� ��� (�źϸ��̸� ������ ������)
  �� ȭ���� �ſ�ó�� �¿� �����ؼ� ������ (mirror: false�� �� �� ����)


[���ǻ���]
  - ī�޶�� ����, ������ ��ó�� �� ��. �н��� �� ī�޶�(��Ʈ�� ȭ�� ���� ����)�� �����̸�
    ������ Ʋ�����Ƿ� c Ű�� �ٽ� �н��� ��
  - �źϸ� �ڼ��� �ʹ� �����ؼ� �н��ϸ� ��� �ڼ��� ������. "��� �ϴ� ���� �ڼ�" ������ ������ ��
  - �н��� �� ����� �� �� �������� ���� ���� ���� ������ (�α׿� ����� ����) -> ���� ���̸� �źϸ����� �� �� ������
    ������� ������ �ϰ� c Ű�� �ٽ� �н��� ��
  - ���� ���� ũ��(30�� �Ѱ�) ���̸� ��� ������ ���ִ� ��ŭ �� ������ �źϸ��� ������ ���� ���� ����
  - ��� 10%�� ���� �н��� �źϸ��� 1/10(�� 0.6cm)�� ���͵� ���. ������ �������� ���ϸ� 15~20���� �ø� ��
  - �Ȱ��� ��������, ����ũ�� ������ ���� ������ �ν��� �� ��
  - model_complexity: 1(�⺻)�� �� ��Ȯ. ��������̰� �ʹ� ������ 0���� (��� ù ���� �� �ٿ�ε�)
  - ������ �ʹ� �����ϰų� ���ϸ� config.json�� warning_pct, danger_pct, danger_after_sec ���ڸ� ����
    (���� ������ "�н��� �źϸ��� �� %��ŭ ���� ���Գ�". �н� �� �źϸ��� ũ�� �ϸ� �������� �۰� �ϸ� ��������)
  - config.json�� �ٲٸ� ���α׷��� ���� �Ѿ� �ݿ���
  - ��� �������� �Ǻ��� �� posture_data.db�� ���� ����ǰ�, �״��� ���� ��Ʈ(server_url)�� ���۵�
    ������ ���� �ְų� ������ �� �Ǹ� DB�� ���� �ξ��ٰ�, ����Ǹ� ������ �ͺ��� �ڵ� ����
    (���α׷��� ���� �ѵ� ���� �ְ�, ���� �ð��� ���� �ð� �״�� �����)
  - posture_data.db�� ���� ��ϵ� ��� ���� (save_interval 3�ʸ� �Ϸ� �� 2.9�� ��, �� 6MB)
    -> �����ϰ� ������ ���α׷��� ���� ����. ��, ���� �� ���� �����͵� ���� �����
  - ī�޶� â�� ����Ͱ� ���� ���� ��. ��������̸� SSH�� �����ϰų� ���� �� �ڵ� ����(systemd)�ϸ�
    â ���� ����� (���� �ƴ�). â�� �Ϻη� ������ config.json�� "show_window": false
  - ���� ����� posture.log ���Ͽ� ����. ������ ����� �� ������ Ȯ��
    (������ ������ ���������� ��/�Ʒ��� ���� �Ÿ������� ���ӡ���� ��� ���ΰ� ���Ƽ� ���� ������ �� �� ����)


[���� ������ �޽����� �ذ�]
  "���� ����, DB�� ���� �� N��"         -> �����ʹ� posture_data.db�� �����ϰ� ���� ��. �Ʒ� ���� �ذ��ϸ� �ڵ� ����
  "���� ���� ... timed out"            -> server_url�� IP�� Ʋ�Ȱų�, ������ �ٸ� ��Ʈ��ũ�� ����
  "���� ���� ... Connection refused"   -> ����(app.py)�� ���� ����
  "ī�޶� ���� ����, 5�� �� ��õ�"     -> ��ķ ���� Ȯ�� / �ٸ� ���α׷��� ī�޶� ��� ��
                                         ������: ���� > ���� ���� > ī�޶� > ����ũ�� �� ���
  "config.json ���� ����: N��° ��"     -> �� �� ��ó�� ��ǥ, ����ǥ Ȯ��
                                         (�ѱ� ����ǥ �� ��, ������ �� �� ��ǥ, True �빮�� ��)
  "������ �� �ٿ�ε� ����, �⺻ �𵨷� ����" -> (model_complexity 0�� ��) ���ͳ��� ���� ��. �ڵ� �ذ��
  "�źϸ� ���� N��°: �� �� Xcm ... -> ����" -> �źϸ� �ڼ����� ���� ���� �� ������. �Ӹ��� �� ������ (������ �״��)
                                         "��鸲"�� ũ�� ������ �����ϴ� 3�� ���� ������ �ֱ�
  "has no attribute 'solutions'"       -> mediapipe ������ �ʹ� �ֽ�. pip install mediapipe==0.10.18
  "DLL load failed" (������)           -> Visual C++ ����� ��Ű�� ��ġ �ʿ� (������ ���� �ʿ�)
  "No module named ..."               -> ����ȯ��(venv)�� python���� �����ߴ��� Ȯ��
"""
import os
import sys
import math
import statistics
import json
import time
import signal
from video_stream import FramePublisher
import sqlite3
import threading
import logging
import logging.handlers
import urllib.request
import urllib.error
from datetime import datetime
from collections import deque
import numpy as np   # mediapipe ��ġ �� �Բ� ��ġ��

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
BASELINE_FILE = os.path.join(BASE_DIR, "baseline.json")
LOG_FILE = os.path.join(BASE_DIR, "posture.log")

# �ð� ������ ��� time.monotonic()���� ��: ��������̴� ���� ���� ���ͳ� �ð� ���߱�� �ð谡
# �� �ð��� �ٲ� �� �ִµ�, �׷��� ���� �ð���ī��Ʈ�ٿ��� ������ ���� (��� �ð��� datetime.now ���)
VIS_MIN = 0.6        # �������� �� �� �̻� Ȯ���ϰ� ������ ���
ABSENT_SEC = 1       # ������ �� ���� ȭ���� �̸�ŭ �̾����� �ڸ� ������� ó�� (���� ����)
LOCAL_DB = os.path.join(BASE_DIR, "posture_data.db")   # ���� ��� ���� + ���� ��� (�ڵ� ����)

# ����� Pose(�� 33��)�� 11, 12�� / ���� Face Mesh(�� 468��) ���
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
ARM_POINTS = (13, 14)   # ���� �Ȳ�ġ: ������� ���� �ö󰡸� ���� �� ��
                        # (�ո� �ö� �� ���⡤�Ȱ� ������� ��� ���� ���� �� �������� �״�� ���)
EDGE_Y = 0.95   # ����� ȭ�� ������ �� �������� �Ʒ��� ȭ�� ���� ������ ��ġ�� ��� �� ��

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000,
                                                   backupCount=3, encoding="utf-8"),
              logging.StreamHandler()],
)
log = logging.getLogger("posture")

running = True


def stop(signum, frame):
    global running
    log.info("���� ��ȣ ����")
    running = False


def load_json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:   # -sig: �޸��� BOM ���嵵 ����
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        log.error(f"{os.path.basename(path)} ���� ����: {e.lineno}��° �� {e.colno}��° ĭ ��ó ({e.msg})")
        return None


# ======================== ���� ========================
send_lock = threading.Lock()
# ������ ���� �� ���Ͻ� ����(http_proxy ȯ�溯��)�� �����ϰ� ���� ����.
# ���������(������)�� ���Ͻð� ������ ������ 127.0.0.1�� ������ �ͱ��� ���Ͻ÷� ���� �����ϱ� ����
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
SEND_TIMEOUT = 5   # ��������̴� �Ǻ� ������� �ٺ��� ���� ������ 1�ʸ� �ѱ�⵵ ��


def _local_db():
    """�Ǻ��� �� DB(posture_data.db). ��� �������� �����ϰ�, sent=1�̸� ������ ���� ��"""
    conn = sqlite3.connect(LOCAL_DB, timeout=5)
    conn.execute("CREATE TABLE IF NOT EXISTS records "
                 "(id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, sent INTEGER DEFAULT 0)")
    return conn


def unsent_count():
    """���� ������ �� ���� ����"""
    conn = _local_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM records WHERE sent = 0").fetchone()[0]
    finally:
        conn.close()


def send(rec, url):
    """�������� posture_data.db�� ������ ��, �� ���� ���� ������ ������ ���� ��Ʈ(server_url)�� ����.
    ������ ���� ������ DB�� ���� �ξ��ٰ� ���� ���� ��(���α׷��� �ٽ� �� �ڿ���) ����"""
    conn = _local_db()
    try:
        conn.execute("INSERT INTO records (data) VALUES (?)", (json.dumps(rec, ensure_ascii=False),))
        conn.commit()
    finally:
        conn.close()
    if not send_lock.acquire(blocking=False):
        return   # ���� ������ ���� ���� ���̸� ���常
    try:
        _flush(url)
    finally:
        send_lock.release()


def _flush(url):
    conn = _local_db()
    sent = 0
    try:
        rows = conn.execute("SELECT id, data FROM records WHERE sent = 0 ORDER BY id").fetchall()
        for rid, data in rows:
            try:
                req = urllib.request.Request(url, data=data.encode("utf-8"),
                                             headers={"Content-Type": "application/json"}, method="POST")
                _opener.open(req, timeout=SEND_TIMEOUT).close()  # 4xx/5xx�� ���� �߻�
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:   # ������ ���� ������ �ź�: �ٽ� ������ �� �ǹǷ� �ǳʶ� (�� �����Ͱ� ������ �ʰ�)
                    log.error(f"������ �����͸� �ź��� �ǳʶ� ({e.code}): {data}")
                    conn.execute("UPDATE records SET sent = 2 WHERE id = ?", (rid,))
                    conn.commit()
                    continue
                log.warning(f"���� ����, DB�� ���� �� {len(rows) - sent}��: {e}")
                break
            except Exception as e:
                log.warning(f"���� ����, DB�� ���� �� {len(rows) - sent}��: {e}")
                break
            conn.execute("UPDATE records SET sent = 1 WHERE id = ?", (rid,))
            conn.commit()
            sent += 1
    finally:
        conn.close()
    if sent > 1:
        log.info(f"�и� ������ {sent}�� ���� �Ϸ�")



# ======================== Ư¡�� ��� ========================
# �� 3D ����(cm): MediaPipe ǥ�� �� ����(canonical_face_model, Apache 2.0)����
# ǥ���� �ٲ� ���� �� �����̴� 33��(���ຼ���� �������롤�̸�)�� ��� ��.
# ���� �������� ��鸲�� ��յǾ� �Ӹ� ��ġ���Ÿ��� �ξ� ������ (���� 6�� -> 33��)
# ��ǥ ����: x ������, y �Ʒ�, z ī�޶󿡼� �־����� ��, ������ �ڳ�
FACE_MODEL = {
    1: (0.0, -0.0, -0.0),
    4: (0.0, -0.66, -0.11),
    5: (0.0, -1.49, 0.23),
    195: (0.0, -2.19, 0.7),
    197: (0.0, -2.86, 1.16),
    6: (0.0, -3.6, 1.69),
    168: (0.0, -4.4, 2.24),
    8: (0.0, -5.15, 2.19),
    9: (0.0, -6.01, 2.09),
    151: (0.0, -7.67, 2.45),
    10: (0.0, -9.39, 2.99),
    98: (-1.41, 0.59, 2.23),
    327: (1.41, 0.59, 2.23),
    129: (-1.79, -0.15, 2.63),
    358: (1.79, -0.15, 2.63),
    33: (-4.45, -3.79, 4.3),
    263: (4.45, -3.79, 4.3),
    133: (-1.86, -3.71, 3.72),
    362: (1.86, -3.71, 3.72),
    116: (-6.47, -2.06, 5.79),
    345: (6.47, -2.06, 5.79),
    123: (-6.34, -0.6, 5.59),
    352: (6.34, -0.6, 5.59),
    50: (-4.77, -0.43, 3.94),
    280: (4.77, -0.43, 3.94),
    54: (-6.28, -7.74, 6.05),
    284: (6.28, -7.74, 6.05),
    103: (-5.13, -8.61, 4.82),
    332: (5.13, -8.61, 4.82),
    67: (-3.52, -9.13, 3.75),
    297: (3.52, -9.13, 3.75),
    109: (-1.89, -9.36, 3.2),
    338: (1.89, -9.36, 3.2),
}
FACE_IDX = list(FACE_MODEL)
FACE_3D = np.array([FACE_MODEL[i] for i in FACE_IDX], dtype=np.float64)
# ��(���� �� �� ���) ��ġ: �ڳ����� 1.8cm ��, 9.9cm ��.
# �źϸ� ������ �ڰ� �ƴ϶� �� ��ġ�� �� -> ������ ���̰ų� ������ ���� �Ͱ� ���� �� �������� ������ �پ��
EAR_3D = np.array([0.0, -1.8, 9.9])

CAMERA_TILT = 10          # ī�޶� �Ʒ��� ������ ����(��). main()���� config�� camera_tilt_deg�� �ٲ�
TORSO_LEN = 50.0           # ������~��� ����(cm). ���� ��� �ٻ� (���� ���� ��꿡 ���)
SHOULDER_MEMORY_SEC = 10   # ���� ��� ��� ���� �� ���� ��, ���������� ���� �� �ִ� ����� �� �ð� ���� ���
FACE_HIDDEN_HOLD = 3       # ����� ���̴µ� �󱼸� �������� ��(�� ��) ������ ������ �����ϴ� �ð�(��)
SH_JUMP = 0.3             # ��� �ʺ� �� ���� 30% �Ѱ� �ٲ�� Ƥ ������ �� (���� 0.2�ʿ� �׸�ŭ �����̱� �����)
MEMORY_TRUST_SEC = 1.0     # ����� ����� ���� ���ȿ��� ������ �� �ð� �̻� ��� ���ƾ� �ø�
                           # (���� �����鼭 ���� ���̴� ����ó��, ����� ����� ���� ������ ��߳��� ª�� ������ ���� ����)


def head_pose(cv2, face_lm, w, h, fov_deg=65):
    """�� 33���� 3D ������ ����(solvePnP) ���� ������ī�޶���� �Ÿ�(cm)������ 3D ��ġ�� ����.
    fov_deg: ī�޶� ���� ȭ��. ��Ʈ�ϡ������ ��ķ�� ���� 60~78��"""
    pts = np.array([(face_lm[i].x * w, face_lm[i].y * h) for i in FACE_IDX], dtype=np.float64)
    f = (w / 2) / math.tan(math.radians(fov_deg) / 2)   # ȭ������ ���� �����Ÿ�(�ȼ�)
    cam = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]], dtype=np.float64)
    flag = getattr(cv2, "SOLVEPNP_SQPNP", cv2.SOLVEPNP_ITERATIVE)
    ok, rvec, tvec = cv2.solvePnP(FACE_3D, pts, cam, None, flags=flag)
    if not ok or tvec[2, 0] <= 0:
        return None
    R = cv2.Rodrigues(rvec)[0]
    fx, fy, fz = R @ np.array([0.0, 0.0, -1.0])   # ���� ���� ����
    ear = R @ EAR_3D + tvec[:, 0]
    return {"pitch": math.degrees(math.atan2(fy, -fz)),   # +: ���� ����
            "yaw": math.degrees(math.atan2(fx, -fz)),     # �¿�� ���� ����
            "dist": tvec[2, 0],                           # ī�޶���� �Ÿ� (cm)
            "ear": ear.tolist(),                          # ���� 3D ��ġ (cm, ī�޶� ����)
            "f": f}


def shoulder_problem(pose_lm):
    """��� ���� �� �ϴ� ����. ���� �� ������ None
    "hidden": �� �� ���̰ų� ȭ�� �Ʒ� ���� �ɸ�(Pose�� ������ ��ġ)
    "arms"  : �Ȳ�ġ�� ������� �� (���� ��� ��� ���� ���� ���� ������)
    "twist" : ���� ���� ������ ���ư� (��� �ʺ�� �Ÿ��� ��µ� ��Ʋ�� ���� ����)"""
    shoulders = (LEFT_SHOULDER, RIGHT_SHOULDER)
    if min(pose_lm[i].visibility for i in shoulders) < VIS_MIN:
        return "hidden"
    if max(pose_lm[i].y for i in shoulders) > EDGE_Y:
        return "hidden"
    top = min(pose_lm[i].y for i in shoulders) - 0.05   # ������� ȭ�� ������ 5% �̻� ������ '�� ��'
    if any(pose_lm[i].visibility >= 0.5 and pose_lm[i].y < top for i in ARM_POINTS):   # (��� �������� ����)
        return "arms"
    ls, rs = pose_lm[LEFT_SHOULDER], pose_lm[RIGHT_SHOULDER]
    if abs(ls.z - rs.z) >= 1.5 * abs(ls.x - rs.x):   # z(�յ�)�� ���� ���������� ũ�� ������, ���� ������ ������ ����
        return "twist"                                # (���� ��ư �� neck_offset���� '���̰� �¾ƾ� ����'�� �ɷ���)
    return None


def get_features(cv2, pose_lm, face_lm, w, h, fov_deg=65, use_shoulders=True):
    """({"pose": head_pose ���, "shoulder": ���(�ȼ�) �Ǵ� None, "tilt": ��� ���� �Ǵ� None, ...}, None)
    �Ǵ� ������ �� ���� �� (None, ȭ�鿡 ��� ����)"""
    if face_lm is None:
        return None, "FACE NOT FOUND - look at camera"
    hp = head_pose(cv2, face_lm, w, h, fov_deg)
    if hp is None:
        return None, "FACE NOT FOUND - look at camera"
    if abs(hp["yaw"]) > 35:
        return None, "TURN TO CAMERA"
    feats = {"pose": hp, "c": (w / 2, h / 2), "shoulder": None, "tilt": None, "sh_problem": "hidden"}

    # ���: ���� �� �ְ�, ���� �� ��� ���̿� ���� ����(���� ������� Ȯ��) ���
    if use_shoulders and pose_lm is not None:
        feats["sh_problem"] = shoulder_problem(pose_lm)
    if feats["sh_problem"] is None:
        ls = (pose_lm[LEFT_SHOULDER].x * w, pose_lm[LEFT_SHOULDER].y * h)
        rs = (pose_lm[RIGHT_SHOULDER].x * w, pose_lm[RIGHT_SHOULDER].y * h)
        nose_x, sw = face_lm[1].x * w, math.dist(ls, rs)
        if sw > 1 and min(ls[0], rs[0]) < nose_x < max(ls[0], rs[0]):
            feats["shoulder"] = {"x": (ls[0] + rs[0]) / 2, "y": (ls[1] + rs[1]) / 2, "sw": sw}
            feats["tilt"] = math.degrees(math.atan2(abs(ls[1] - rs[1]), abs(ls[0] - rs[0])))   # ��� ����
        else:
            feats["sh_problem"] = "hidden"
    return feats, None


def shoulder_3d(sh, f, c, z):
    """��� ���(�ȼ�)�� �Ÿ�(cm) -> ī�޶� ���� 3D ��ġ(cm)"""
    return np.array([(sh["x"] - c[0]) / f * z, (sh["y"] - c[1]) / f * z, z])


def make_base(good):
    """�ٸ� �ڼ� ���������� ������ ����: �� ��ġ, ��� ��ġ, ��~��� �Ÿ�.
    ��� ���� �ʺ�� �𸣹Ƿ� '�ٸ� �ڼ������� ����� �Ϳ� ���� �Ÿ��� �ִ�'�� ���� ����"""
    ear0 = np.median([g["pose"]["ear"] for g in good], axis=0)
    base = {"version": MODEL_VERSION, "ear": ear0.tolist()}
    with_sh = [g for g in good if g.get("sh_use")]
    if len(with_sh) >= 0.7 * len(good):
        f, c = good[0]["pose"]["f"], good[0]["c"]
        sh = {k: statistics.median(g["sh_use"][k] for g in with_sh) for k in ("x", "y", "sw")}
        # �ٸ� �ڼ����� ����� �� �ٷ� �Ʒ�. ī�޶� camera_tilt_deg��ŭ �����ٺ���
        # ����� �ͺ��� (��~��� ���� x sin ����)��ŭ ī�޶󿡼� �� �ָ� ����
        z0 = ear0[2]
        for _ in range(3):
            gap = shoulder_3d(sh, f, c, z0)[1] - ear0[1]     # ȭ�� ���� ��~��� ���� ����(cm)
            z0 = ear0[2] + gap * math.tan(math.radians(CAMERA_TILT))
        sh0 = shoulder_3d(sh, f, c, z0)
        base.update(sw0=sh["sw"], sh=sh0.tolist(), neck=float(np.linalg.norm(ear0 - sh0)))
        tilts = [g["tilt"] for g in with_sh if g["tilt"] is not None]
        if tilts:
            base["tilt"] = statistics.median(tilts)
    return base


def neck_offset(feats, base):
    """�Ͱ� �ٸ� �ڼ����� ������/�Ʒ��� ������ �Ÿ�(cm) �߿��� '������ �������� ���� ��ŭ'�� �� ����,
    ���� ���� ����(��, ������)�� ������.
    �������� ������ ������ ���̸�(ô�� �߸�) ������-���-�Ͱ� �� ����ó�� ���� ���Ƽ�,
    �ʹ� ����� ������ ��ŭ�� (����+��)/���� ��(�� 1.3��) ������. �׸�ŭ ���� '�� ������ ��'�� ����
    -> �������� ���̱�, �ڷ� ����, ����° �ٰ������ �źϸ����� �� ��
    ��� �յ� ��ġ�� ��� �ʺ��(��������� �а� ����), ���Ʒ��� ȭ�� �� ��� ���̷� ����"""
    ear, ear0 = np.array(feats["pose"]["ear"]), np.array(base["ear"])
    move = ear - ear0
    lean = 0.0
    sh = feats.get("sh_use")
    if sh is not None and "sw0" in base:
        sh0 = np.array(base["sh"])
        z = sh0[2] * base["sw0"] / sh["sw"]                 # ������� �Ÿ�
        sh_move = shoulder_3d(sh, feats["pose"]["f"], feats["c"], z) - sh0
        sh_move[0] = 0.0                                    # �¿� �̵��� �źϸ�� �������
        # ����� �־��� ���̸�(���� ����) �ڷ� ���� �Ǵ� �� ��Ʋ��.
        # �ڷ� ���� ����� ȭ�鿡�� ���ε� �ö󰡰�, ��Ʋ�� ���̴� �״�� -> ���̰� �´� ��ŭ�� '����'�� ����
        # (��Ʋ�⸦ ����� �߸� ���� �Ͱ� ������ ���� ��ó�� ���Ǳ� ����)
        if sh_move[2] > 0:
            f = feats["pose"]["f"]
            expect = f * sh0[1] / (sh0[2] + sh_move[2]) - f * sh0[1] / sh0[2]   # ���ٸ� ȭ�� ���� ��ȭ(�ȼ�)
            actual = (sh["y"] - feats["c"][1]) - f * sh0[1] / sh0[2]
            agree = min(max(actual / expect, 0.0), 1.0) if expect < -2 else 0.0
            agree = max(agree - 0.5, 0.0) * 2   # ���̰� ���� �̻� �¾ƾ� ����� ���� (��鸲���� ���� �´� �� ����)
            sh_move[2] = max(sh_move[2] - 2.0, 0.0) * agree   # 2cm �̳��� ��鸲���������� ���� ����
        # ����� ���� �������ٴµ� �ʹ� ���� �״�θ�, ���� ������ �� �ƴ϶� ��� ������ Ʋ�� ��
        # (���� �������� Pose�� ��� �ʺ� ������ �־ 10~20%�� �ٲ�� ��찡 ����).
        # ������ �����̸� �ʹ� ������� �� ����(�� 1.3��) �����̹Ƿ�, �� �������� ����� 20% ���ϸ� ����
        if abs(sh_move[2]) > 2.0:
            ratio = abs(move[2]) / abs(sh_move[2])
            sh_move[2] *= min(max((ratio - 0.2) / 0.3, 0.0), 1.0)
        # ����� ���� �ö󰡴� �� �ڷ� ��� ����. �� �ۿ�(�յڷ� �� �����̰ų� ������ ���� ��) �ö󰡸�
        # ��� �����̹Ƿ� ���� (�� �׷��� �Ͱ� �Ʒ��� ������ ��ó�� ����)
        sh_move[1] = max(sh_move[1], -0.6 * max(sh_move[2], 0.0))
        body = (TORSO_LEN + base["neck"]) / TORSO_LEN * sh_move   # ������ �������� ���� �� �̵�
        move = move - body
        lean = math.degrees(math.asin(max(-1.0, min(1.0, -sh_move[2] / TORSO_LEN))))
        # ���� ���̡�ī�޶� ������ ������� �޶� �� ����� ���� Ʋ�� �� ���� ->
        # ������ ���� �������� ���� �� 12%��ŭ�� '����'�� ���� ���� (���� ũ�� ������ ���� �� �ϰ�)
        margin = 0.12 * float(np.linalg.norm(body))
        fwd, down = -move[2], move[1]
        fwd = max(fwd - margin, 0.0) if fwd > 0 else fwd
        down = max(down - margin / 2, 0.0) if down > 0 else down
        return fwd, down, lean
    return -move[2], move[1], lean                          # ������(ī�޶� ��), �Ʒ���, ���� ����


# ======================== ���� ���� �н� ========================
MIN_SEPARATION = 2.0   # �� �ڼ� ���̰� ���� �ڼ� �ȿ����� ��鸲�� �� �� �̻��̾�� �н� ����
MIN_MOVE_CM = 1.5      # �źϸ� �ڼ����� ���� �ּ� �̸�ŭ(cm)�� �������� �н� ����
MAX_TRIES = 2          # �źϸ� ������ �ִ� 2�� (������ ũ�� �� ���� ��). �� �ڿ��� �ݺ����� �ʰ� �״�� �н�
DEFAULT_DELTA = [5.0, 2.0]   # �� �� �� �źϸ��� ���� �� ������ �� ���� �⺻ �źϸ�(���� �� 5cm, �Ʒ� 2cm)
MODEL_VERSION = 3      # ����� �н� ���(baseline.json) ����. �ٲ�� ���� ������ �ٽ� �н�


def train(good, bad, force=False):
    """�ٸ� �ڼ��� ������ �����, �źϸ� �ڼ����� ���� ���� �������� �󸶳�(cm) ���������� �н�.
    ���� = ���� ���� �������� '�н��� �źϸ� ����'�� ���� �� ���� (�ٸ� �ڼ� 0, �н��� �źϸ� 100).
    force: ���� �� �ٽ� ���������� ������ ���� (1cm �̻� ���������� �н�)
    ��ȯ: (�� �Ǵ� None, ���� ����, �� ������ [�� cm, �Ʒ� cm], ��鸲 cm)"""
    base = make_base(good)
    G = np.array([neck_offset(g, base)[:2] for g in good])
    B = np.array([neck_offset(b, base)[:2] for b in bad])
    # ��� ��� ��� ��: ���� �߿��� '�ֱ� 3���� ��� ��'���� ������ ���Ƿ� ���� ����̾��
    # �ٸ� �ڼ��� 0%�� ���� (����� ���� ���� Ƣ�� �� ������ �ٸ� �ڼ��� 5~10%�� ġ��ħ)
    mg, mb = np.median(G, axis=0), np.median(B, axis=0)
    delta = mb - mg
    size = float(np.linalg.norm(delta))
    if size < 1e-6:
        return None, 0.0, delta.tolist(), 0.0
    proj = np.vstack([G - mg, B - mb]) @ delta / size        # ���� �ڼ� �ȿ����� ��鸲
    noise = max(float(proj.std()), 0.3)                       # ��鸲 �ּ� 0.3cm�� ��
    sep = size / noise
    # �źϸ��� �ݵ�� ���� ������ ���;� �� (������ 1cm �̻�). �Ʒ��θ� ������ �� ���� ������ �� ����
    ok = size >= MIN_MOVE_CM and sep >= MIN_SEPARATION and delta[0] >= 1.0
    if force:   # ���� �� ������ ������ ���� ���� �� (�׷��� ��鸲 �����̸� ����)
        ok = size >= 1.0 and sep >= 1.5 and delta[0] >= 0.7
    if not ok:
        return None, sep, delta.tolist(), noise
    base.update(good=mg.tolist(), delta=delta.tolist())
    return base, sep, delta.tolist(), noise


def train_default(good):
    """�źϸ� �ڼ��� �� �� �� ����� �� ���� ��: �ٸ� �ڼ��� �״�� ����, �źϸ��� ������� ������ ����
    (����ڿ��� ��� �ݺ���Ű�� �ʱ� ����)"""
    base = make_base(good)
    G = np.array([neck_offset(g, base)[:2] for g in good])
    base.update(good=np.median(G, axis=0).tolist(), delta=list(DEFAULT_DELTA), default=True)
    return base


def can_judge(model, feats):
    """������� �Ἥ �н��ߴµ� ���� ����� �𸣸�, ���� �������� �� �� ��� �������� ����"""
    return "sw0" not in model or feats.get("sh_use") is not None


def posture_score(model, feats):
    """0 = �ٸ� �ڼ�, 100 = �н��� �źϸ�.
    ���� ���� ������(������, �Ʒ��� cm)�� '�н��� �źϸ� ����'�� ���� �� ����.
    �н� ������ ������ �ʰ� �Ӹ��� ���о ������ ���� ��ŭ ������ ����"""
    fwd, down, _ = neck_offset(feats, model)
    x = np.array([fwd, down]) - np.array(model["good"])
    d = np.array(model["delta"])
    return float(x @ d / (d @ d)) * 100


class Smooth:
    """�͡���� �������� ��� '���� �ð�(tau��)��ŭ' �ε巴�� ��.
    �Ϳ� ����� �Ȱ��� �ʾ����� ���� ��߳��� �ʾƼ�, ���� �����̴� ������ ������ Ƣ�� ����.
    ������ ���� ���� �� ����(still_tau) �ε巴�� �ؼ� ��鸲�� ���̰�, �����̸� ������(tau) ����.
    (�Ϳ� ����� �׻� ���� ���� ���Ƿ� ���� ��߳��� ����)"""
    def __init__(self, tau=0.25, still_tau=0.6):
        self.fast, self.still = tau, max(still_tau, tau)
        self.tau, self.v, self.t = tau, {}, {}
        self.jumped = False   # ���� ��� ���� 'Ƥ ��'���� ���ȴ���

    def adapt(self, ear):
        """�Ͱ� �ε巴�� �� ��ġ���� �󸶳� �������(cm)�� �̹��� �� tau�� ����"""
        if "ear" not in self.v:
            self.tau = self.fast
            return
        dev = float(np.linalg.norm(np.asarray(ear) - self.v["ear"]))
        self.tau = self.fast + (self.still - self.fast) * math.exp(-dev / 0.6)   # 0.6cm �̻� �����̸� ���� ������

    def __call__(self, key, x, now):
        x = np.asarray(x, dtype=np.float64)
        if key not in self.v or now - self.t[key] > 0.5:   # ó���̰ų� �ѵ��� �������� ���� ����
            self.v[key] = x
        else:
            a = 1 - math.exp(-(now - self.t[key]) / self.tau)
            self.v[key] = self.v[key] + a * (x - self.v[key])
        self.t[key] = now
        return self.v[key]


def prepare(sm, feats, now):
    """���� �� �غ�: �͡������ ���� ������ �ε巴�� �ϰ�,
    ���� ����� ���� �� ������(���� �� ��) �ֱٿ� ���� �� �ִ� ���(�ε巴�� �� ��)�� ��� ���"""
    out = dict(feats, pose=dict(feats["pose"]), sh_from_memory=False)
    sm.adapt(feats["pose"]["ear"])
    out["pose"]["ear"] = sm("ear", feats["pose"]["ear"], now).tolist()
    sh = feats["shoulder"]
    cx, cy = feats["c"]
    # ����� (1/�ʺ�, ������ġ/�ʺ�, ������ġ/�ʺ�)�� �ε巴�� �� = ����� 3D ��ġ�� �ε巴�� �ϴ� �Ͱ� ����.
    # �͵� 3D ��ġ�� �ε巴�� �ϹǷ� ���� ��Ȯ�� ���� ������� �ʾ�����, ���� �������� ���� ��߳��� ����
    if sh is not None:
        raw = [1 / sh["sw"], (sh["x"] - cx) / sh["sw"], (sh["y"] - cy) / sh["sw"]]
        prev = sm.v.get("sh") if "sh" in sm.v and now - sm.t["sh"] < 0.5 else None
        # ���� Pose�� ���� �� ���� ��� �ʺ� 30% �Ѱ� �����ϰ� ���� -> �� �� Ƥ ���� ������ ���� �� ���.
        # (�� �� �������� �׷��� ������ ������ ������ ������ ���� �޾Ƶ���)
        if prev is not None and abs(raw[0] - prev[0]) / prev[0] > SH_JUMP and not sm.jumped:
            sm.jumped, v = True, prev
        else:
            sm.jumped = False
            v = sm("sh", raw, now)
    elif feats["sh_problem"] in ("arms", "twist") and "sh" in sm.v and now - sm.t["sh"] < SHOULDER_MEMORY_SEC:
        # ���� ��ų� ��� ��Ʋ���� ���� ��� ��� (������ �״�ζ�� �� �� ����).
        # ����� ȭ�� ������ ���� �� ���� ũ�� ������ ���̶� ����� ���� �� ��
        v, out["sh_from_memory"] = sm.v["sh"], True
    else:
        sm.jumped = False   # ����� ����� 'Ƥ ��' ǥ�õ� �ʱ�ȭ (���� ù ���� �ٽ� �˻�)
        out["sh_use"] = None
        return out
    sw = 1 / v[0]
    out["sh_use"] = {"x": v[1] * sw + cx, "y": v[2] * sw + cy, "sw": sw}
    return out


class OneEuro:
    """������ ������ �� �ٷ� ���󰡰�, ������ ���� �� ������ ��� ���� (One Euro Filter)"""
    def __init__(self, min_cutoff=1.5, beta=0.02):
        self.min_cutoff, self.beta, self.t = min_cutoff, beta, None

    def __call__(self, x, t):
        if self.t is None:
            self.x, self.dx, self.t = x, 0.0, t
            return x
        dt = max(t - self.t, 1e-3)
        self.t = t
        a = lambda fc: 1 / (1 + 1 / (2 * math.pi * fc * dt))
        self.dx += a(1.0) * ((x - self.x) / dt - self.dx)
        self.x += a(self.min_cutoff + self.beta * abs(self.dx)) * (x - self.x)
        return self.x


def raw_status(pct, cfg, prev="����"):
    """���� -> ����/���/����. �̹� ���/�����̸� ������ hysteresis_pct��ŭ ���� ��迡�� �������� �ʰ�"""
    gap = cfg.get("hysteresis_pct", 2)
    warn = cfg["warning_pct"] - (gap if prev != "����" else 0)
    danger = cfg["danger_pct"] - (gap if prev == "����" else 0)
    if pct < warn:
        return "����"
    return "���" if pct < danger else "����"


def hold(raw, since, danger_after_sec, now):
    """��� ������ ������ �ٷ� ���, ���� ������ ���� ���°� danger_after_sec �̾����� ����.
    since: (���� �ڼ� ���� �ð�, ���� ���� ���� �ð�) �Ǵ� None. ��ȯ: (����, since, ���� �ڼ� ���ӽð�)"""
    if raw == "����":
        return "����", None, 0.0
    bad, danger = since or (None, None)
    bad = bad or now
    danger = (danger or now) if raw == "����" else None
    status = "����" if danger is not None and now - danger >= danger_after_sec else "���"
    return status, (bad, danger), now - bad


STATUS_URL = None   # main()���� server_url�� ����. ��) http://127.0.0.1:5050/api/status


def post_status(status):
    """���� ���¸� ���� /api/status�� �ٷ� ���� -> ���������(rpi_device.py)�� �������� LED/����/���� ����.
    �����ص� ���� ���� �����̳� save_interval���� �ٽ� �����Ƿ� ��ϸ� ����"""
    def _post():
        try:
            req = urllib.request.Request(
                STATUS_URL, data=json.dumps({"status": status}, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="POST")
            _opener.open(req, timeout=SEND_TIMEOUT).close()
        except Exception as e:
            log.warning(f"���� �˸� ����: {e}")
    threading.Thread(target=_post, daemon=True).start()


def on_status_change(old, new):
    """���°� �ٲ� �� ȣ��. ������ ���� ���������(rpi_device.py)�� 1�� �ȿ� �˸�"""
    log.info(f"���� ����: {old} -> {new}")
    post_status(new)


# ======================== ȭ�� ǥ�� ========================
STATUS_EN = {"����": "NORMAL", "���": "WARNING", "����": "DANGER"}   # cv2.putText�� �ѱ� ������
STATUS_COLOR = {"����": (0, 200, 0), "���": (0, 165, 255), "����": (0, 0, 255)}  # BGR
GRAY, YELLOW = (160, 160, 160), (0, 220, 255)


def has_display():
    """â�� ��� ȭ���� �ִ���. systemd��SSH ����ó�� ȭ���� ������ False"""
    if not sys.platform.startswith("linux"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


UPPER_BODY = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]   # ȭ�鿡 �׸� ��: ���, ��
FACE_DOTS = (1, 33, 263, 152)                                       # ȭ�鿡 �׸� �� ��: ��, �� ��, ��


def neck_points(feats):
    """ȭ�鿡 �׸� ��(����)�� ��� ��� ��ġ(�ȼ�). �źϸ��̸� �� ���� ������ ������"""
    sh = feats.get("sh_use")
    if sh is None:
        return None
    ex, ey, ez = feats["pose"]["ear"]
    f, (cx, cy) = feats["pose"]["f"], feats["c"]
    return (int(cx + f * ex / ez), int(cy + f * ey / ez)), (int(sh["x"]), int(sh["y"]))


def draw(cv2, mp, frame, pose_res, face_lm, text, color, sub, pct, cfg, fps_text="", neck_line=None, publisher=None, show_window=True):
    """������� ��, �� ��, ��-��� ��, ����, ���� ���븦 �׷��� â�� ǥ��. q: ����, ���� Ű�� ������"""
    global running
    h, w = frame.shape[:2]
    if pose_res is not None and pose_res.pose_landmarks:   # ��ü�� (�ٸ����� ���� ������ �� �Ἥ ����)
        lm = pose_res.pose_landmarks.landmark
        pt = lambda i: (int(lm[i].x * w), int(lm[i].y * h))
        for a, b in UPPER_BODY:
            if lm[a].visibility > 0.5 and lm[b].visibility > 0.5:
                cv2.line(frame, pt(a), pt(b), (255, 255, 255), 2)
        for i in (11, 12):
            if lm[i].visibility > 0.5:
                cv2.circle(frame, pt(i), 5, (0, 0, 255), -1)
    if face_lm is not None:
        for i in FACE_DOTS:
            cv2.circle(frame, (int(face_lm[i].x * w), int(face_lm[i].y * h)), 3, (255, 255, 0), -1)
    if neck_line is not None:
        cv2.line(frame, neck_line[0], neck_line[1], (0, 255, 255), 2)
        cv2.circle(frame, neck_line[0], 6, (0, 255, 255), -1)
    if cfg.get("mirror", True):
        frame = cv2.flip(frame, 1)   # �ſ�ó�� �����ֱ� (���ڴ� ������ �Ŀ� ��)

    cv2.putText(frame, text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 3)
    if sub:
        cv2.putText(frame, sub, (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    if pct is not None:   # ���� ����: 0(�ٸ� �ڼ�) ~ 100(�н��� ���� �ڼ�)
        x0, x1, y0 = 10, w - 10, h - 45
        cv2.rectangle(frame, (x0, y0), (x1, y0 + 15), (80, 80, 80), -1)
        fill = x0 + int((x1 - x0) * min(max(pct, 0), 120) / 120)
        cv2.rectangle(frame, (x0, y0), (fill, y0 + 15), color, -1)
        for th in (cfg["warning_pct"], cfg["danger_pct"]):   # ��������� ���ؼ�
            tx = x0 + int((x1 - x0) * th / 120)
            cv2.line(frame, (tx, y0 - 3), (tx, y0 + 18), (255, 255, 255), 2)
    cv2.putText(frame, "c: recalibrate  q: quit", (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    if fps_text:
        cv2.putText(frame, fps_text, (w - 360, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    if publisher is not None:
        publisher.submit(frame)
    if not show_window:
        return -1
    cv2.imshow("turtle_neck", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        log.info("q Ű �Է�, ����")
        running = False
    return key


def make_pose(mp, complexity=1):
    """1: ��Ȯ(�⺻, ��ġ ���Ͽ� ����) / 0: ������(��������̿�, ù ���� �� �ٿ�ε�).
    0�� �ٿ�ε忡 �����ϸ� 1�� ����"""
    for c in dict.fromkeys((complexity, 1)):
        try:
            return mp.solutions.pose.Pose(model_complexity=c,
                                          min_detection_confidence=0.5,
                                          min_tracking_confidence=0.5)
        except Exception as e:
            if c == 1:
                raise
            log.warning(f"������ �� �ٿ�ε� ����, �⺻ �𵨷� ����: {e}")


# ======================== ī�޶� ========================
def open_camera(cv2, cfg, stop_event):
    """ī�޶� ����. 60fps�� ������ ��κ��� ��ķ�� MJPG ����̾�� �ؼ� ���� MJPG�� ��û.
    �� ������ 5�ʸ��� �ٽ� �õ�"""
    api = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY   # ��������̴� V4L2
    want_w, want_h = cfg.get("camera_width", 640), cfg.get("camera_height", 480)
    want_fps, fourcc = cfg.get("camera_fps", 60), cfg.get("camera_fourcc", "MJPG")
    while running and not stop_event.is_set():
        cap = cv2.VideoCapture(cfg.get("camera_index", 0), api)
        if cap.isOpened():
            if fourcc:   # �ػ󵵺��� ���� ���ؾ� ����Ǵ� ī�޶� ����
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, want_w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, want_h)
            cap.set(cv2.CAP_PROP_FPS, want_fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)       # ������ ȭ���� �׾� ���� ���� (�����ϴ� ī�޶�)
            log.info(f"ī�޶� ���� ���� (��û {want_w}x{want_h} {want_fps}fps -> ī�޶� ���� "
                     f"{cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f} "
                     f"{cap.get(cv2.CAP_PROP_FPS):.0f}fps)")
            return cap
        cap.release()
        log.warning("ī�޶� ���� ����, 5�� �� ��õ�")
        stop_event.wait(5)
    return None


class Rate:
    """�ʴ� ó�� Ƚ��(fps) ����"""
    def __init__(self):
        self.n, self.t0, self.value = 0, time.monotonic(), 0.0

    def tick(self):
        self.n += 1
        dt = time.monotonic() - self.t0
        if dt >= 2:
            self.value, self.n, self.t0 = self.n / dt, 0, time.monotonic()


class CameraThread(threading.Thread):
    """ī�޶� �б� ���� ������. �׻� '���� �ֱ� ȭ��' �ϳ��� �����ؼ�,
    �м��� ������ ������ ȭ���� ������ ����. �� ȭ���� ���� ��ٸ��� ��������� ����"""
    def __init__(self, cv2, cfg, stop_event):
        super().__init__(daemon=True, name="camera")
        self.cv2, self.cfg, self.stop_event = cv2, cfg, stop_event
        self.cond = threading.Condition()
        self.frame, self.seq, self.shape, self.rate = None, 0, (480, 640), Rate()

    def run(self):
        cap, checked = None, False
        try:
            while running and not self.stop_event.is_set():
                if cap is None:
                    cap = open_camera(self.cv2, self.cfg, self.stop_event)
                    if cap is None:
                        break
                    opened_at = time.monotonic()
                ok, frame = cap.read()
                if not ok:
                    log.warning("������ �б� ����, ī�޶� �翬��")
                    cap.release()
                    cap = None
                    continue
                with self.cond:
                    self.frame, self.seq, self.shape = frame, self.seq + 1, frame.shape[:2]
                    self.cond.notify_all()
                self.rate.tick()
                if not checked and time.monotonic() - opened_at > 5:   # ������ ������ �ӵ� �� �� Ȯ��
                    checked, want = True, self.cfg.get("camera_fps", 60)
                    log.info(f"ī�޶� ���� �ӵ� {self.rate.value:.0f}fps (��û {want}fps)")
                    if self.rate.value < want * 0.8:
                        log.warning("ī�޶� ��û�� �ӵ����� ���� -> ��ķ�� �� �ӵ��� �������� �ʰų�, "
                                    "������ ��ο� ���� �ð��� ����� �� (������ ���)")
        except Exception:
            log.exception("ī�޶� ������ ����")
        finally:
            if cap is not None:
                cap.release()
            with self.cond:
                self.cond.notify_all()

    def latest(self):
        with self.cond:
            return self.seq, self.frame

    def wait_new(self, last_seq, timeout):
        """last_seq ���� ȭ���� �� ������ ��ٸ� (��� Ȯ���ϸ� CPU�� ���� ����). �ð� �ʰ��� (last_seq, None)"""
        with self.cond:
            self.cond.wait_for(lambda: self.seq != last_seq or self.stop_event.is_set(), timeout)
            return (self.seq, self.frame) if self.seq != last_seq else (last_seq, None)


class ModelThread(threading.Thread):
    """MediaPipe �� �ϳ��� �����ϴ� ������ (�󱼿� 1��, ����� 1��).
    - MediaPipe�� ����ϴ� ���� ���̽� ���(GIL)�� Ǯ�� �༭, �����帶�� �ٸ� CPU �ھ�� ���ÿ� ����
    - �� ȭ���� ���� ����, �ʴ� fps�������� ����ϰ� ���� �ð��� �� -> CPU�� �� ���� ����"""
    def __init__(self, name, cv2, make_model, pick, camera, fps, stop_event, prep=None):
        super().__init__(daemon=True, name=name)
        self.cv2, self.make_model, self.pick, self.camera = cv2, make_model, pick, camera
        self.prep = prep or (lambda frame: (frame, None))   # ��� ���� ȭ���� �߶󳻴� �� (�⺻: �״��)
        self.interval, self.stop_event = 1 / max(fps, 0.5), stop_event
        self.cond = threading.Condition()
        self.result, self.stamp, self.id, self.rate = None, 0.0, 0, Rate()
        self.frame_seq, self.history = -1, deque(maxlen=90)   # ����� ���� ȭ�� ��ȣ, �ֱ� �����

    def run(self):
        try:
            with self.make_model() as model:
                last_seq = -1
                while running and not self.stop_event.is_set():
                    start = time.monotonic()
                    seq, frame = self.camera.wait_new(last_seq, 0.5)
                    if frame is None:
                        continue
                    last_seq = seq
                    img, meta = self.prep(frame)
                    rgb = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2RGB)
                    rgb.flags.writeable = False   # ���� ���� �Ѱܼ� ���� �� ������
                    out = self.pick(model.process(rgb), meta)
                    with self.cond:
                        self.result, self.stamp, self.id, self.frame_seq = out, time.monotonic(), self.id + 1, seq
                        self.history.append((seq, out))
                        self.cond.notify_all()
                    self.rate.tick()
                    self.stop_event.wait(max(0.0, self.interval - (time.monotonic() - start)))   # ���� �ð��� ��
        except Exception:
            log.exception(f"{self.name} ������ ����")
        finally:
            with self.cond:
                self.cond.notify_all()

    def latest(self):
        with self.cond:
            return self.id, self.result, self.stamp

    def latest_full(self):
        with self.cond:
            return self.id, self.result, self.stamp, self.frame_seq

    def find(self, seq):
        """ȭ�� ��ȣ seq�� ����(������ ���� �����) ȭ���� ���. ������ ���� �ֱ� ���"""
        with self.cond:
            if not self.history:
                return self.result
            return min(self.history, key=lambda h: abs(h[0] - seq))[1]

    def wait_new(self, last_id, timeout):
        """�� ����� ���� ������ ��ٸ�. �ð� �ʰ��� ���� ��� �״��"""
        with self.cond:
            self.cond.wait_for(lambda: self.id != last_id or self.stop_event.is_set(), timeout)
            return self.id, self.result, self.stamp


POSE_MAX_AGE = 1.0   # ��� ����� �̺��� ���������� ���� ����(��)


class Target:
    """ó�� ���� �� ����� ��� ����. ���� �߿� �ٸ� ����� ȭ�鿡 ���͵� ����.
    - ó������ ���� ũ��(������) ���̴� ���� ����
    - �״������ʹ� �ٷ� �� ��ġ���� ���� ����� �󱼸� ���� ������� �� (�ʹ� �ָ� ������ �ٸ� ���)
    - release_sec ���� �� ���̸� ������ (���� ����� ���� ���� �� �ְ�)
    - ���(Pose)�� �� ��� �ֺ��� �߶� ��� -> �ٸ� ����� ����� ���� ����"""
    def __init__(self, release_sec=5):
        self.release_sec = release_sec
        self.center, self.size, self.seen = None, 0.0, 0.0
        self.box = None          # ��� �������� �߶� ���� (�ȼ�, ��� �����尡 ����)
        self.lock_id = 0         # �� ����� ���� ������ 1�� �þ (����� �ٲ������ Ȯ�ο�)

    @staticmethod
    def _measure(lm, w, h):
        a, b = lm[33], lm[263]   # ���� �� �ٱ� ��
        return ((a.x + b.x) / 2 * w, (a.y + b.y) / 2 * h), max(math.hypot((a.x - b.x) * w, (a.y - b.y) * h), 1.0)

    def pick(self, faces, w, h, now):
        """�� ���� �� �� ���󰡴� ����� ��. ������ None"""
        if self.center is not None and now - self.seen > self.release_sec:
            log.info("���󰡴� ����� �� ���� -> ���� ����� ���� ����")
            self.center, self.box = None, None
        if not faces:
            return None
        cands = [(self._measure(f, w, h), f) for f in faces]
        if self.center is None:                         # ó��: ���� ũ�� ���̴�(�����) ���
            (c, size), face = max(cands, key=lambda x: x[0][1])
            self.lock_id += 1
            log.info(f"���� ����� ���� ({self.lock_id}��°)")
        else:
            (c, size), face = min(cands, key=lambda x: math.dist(x[0][0], self.center))
            if math.dist(c, self.center) > max(3 * self.size, 0.15 * w):
                return None                             # �ٸ� ��� -> ����
        self.center, self.size, self.seen = c, size, now
        # ������ȱ��� ���� ����: �� ���� �Ÿ�(s)�� ���� ��5��, �� 5��(�� ���), �Ʒ� 7��
        s_ = size
        box = (max(0, c[0] - 5 * s_), max(0, c[1] - 5 * s_), min(w, c[0] + 5 * s_), min(h, c[1] + 7 * s_))
        if self.box is None or max(abs(a - b) for a, b in zip(box, self.box)) > 0.5 * s_:
            self.box = box                              # ���ݾ� ��鸱 ���� �״�� (��� ������ ������)
        return face


def pose_prep(target):
    """��� ��� ��: ���󰡴� ��� �ֺ��� �߶� (���� �ƹ��� �� ������� ȭ�� ��ü)"""
    def prep(frame):
        box = target.box
        if box is None:
            return frame, None
        x0, y0, x1, y1 = (int(v) for v in box)
        if x1 - x0 < 32 or y1 - y0 < 32:
            return frame, None
        return frame[y0:y1, x0:x1], (x0, y0, x1 - x0, y1 - y0, frame.shape[1], frame.shape[0])
    return prep


def pose_pick(result, meta):
    """�߶� ȭ�� ���� ��� ��ǥ�� ��ü ȭ�� �������� �ǵ���"""
    if meta is None or not result.pose_landmarks:
        return result
    from mediapipe.framework.formats import landmark_pb2
    x0, y0, cw, ch, w, h = meta
    out = landmark_pb2.NormalizedLandmarkList()
    for p in result.pose_landmarks.landmark:
        out.landmark.add(x=(p.x * cw + x0) / w, y=(p.y * ch + y0) / h, z=p.z * cw / w, visibility=p.visibility)
    result.pose_landmarks = out
    return result


# ======================== ���� ���� ========================
READY_SEC = 3   # ���� �ܰ踶�� �غ� ī��Ʈ�ٿ�(��)


def run(cfg):
    import cv2
    import mediapipe as mp

    stop_event = threading.Event()   # run()�� ������ ������鵵 ���� ������ ���� ��ȣ
    camera = CameraThread(cv2, cfg, stop_event)
    face_thread = ModelThread(
        "face", cv2,
        lambda: mp.solutions.face_mesh.FaceMesh(max_num_faces=3, min_detection_confidence=0.5,
                                                min_tracking_confidence=0.5),   # ���� �� �� ���� ����� �������� 3������
        lambda r, meta: [f.landmark for f in r.multi_face_landmarks] if r.multi_face_landmarks else [],
        camera, cfg.get("analysis_fps", 30), stop_event)
    target = Target(cfg.get("new_person_reset_sec", 5) or 5)
    pose_thread = None
    if cfg.get("use_shoulders", True):   # ����� �� ���� ���� ���ſ� ����� �ƿ� �� ��
        pose_thread = ModelThread("pose", cv2, lambda: make_pose(mp, cfg.get("model_complexity", 1)),
                                  pose_pick, camera, cfg.get("pose_fps", 5), stop_event, prep=pose_prep(target))
    threads = [t for t in (camera, face_thread, pose_thread) if t is not None]
    for t in threads:
        t.start()
    screen_rate, last_fps_log, fps_text = Rate(), time.monotonic(), ""

    reset_sec = cfg.get("new_person_reset_sec", 5)
    model_lock = 0   # ���� �н������� ���� ��� ��ȣ (Target.lock_id)
    model = load_json(BASELINE_FILE) if reset_sec == 0 else None   # ����ȸ ���� �Ź� ���� �н�
    if model and model.get("version") != MODEL_VERSION:
        model = None   # ���� ���� ���� (�Ÿ� ���� ���� �޶� �ٽ� �н�)
    phase = "run" if model else "wait"   # wait -> good_ready -> good_rec -> bad_ready -> bad_rec -> run
    phase_start, good, bad, retry_msg_until = 0.0, [], [], 0.0
    tries, temp_base, retry_msg = 0, None, ""   # �źϸ� ���� Ƚ��, �ٸ� �ڼ� ����(�н� �� �ȳ���), �ٽ� ���� ����
    filt = OneEuro()
    status, raw, bad_since = "����", "����", None
    last_save = last_valid = time.monotonic()
    last_seen = 0.0
    sm = Smooth(cfg.get("smooth_sec", 0.25))   # �͡������ ���� ������ �ε巴�� (+ �� �� �� ��� ���)
    rise_since = None                           # ����� ����� ������ ������ ������ �ð�
    recent = deque(maxlen=3)                    # �ֱ� ���� 3�� (Ƣ�� �� �ɷ�����)
    pct, duration = None, 0.0
    pose_res, face_lm, text, sub, color = None, None, "STARTING", "", GRAY
    show = cfg.get("show_window", True) and has_display()
    publisher = FramePublisher(cfg) if cfg.get("web_video", True) else None
    if not show:
        log.info("ī�޶� â ���� ���� (����� ���� �Ǵ� show_window=false)")

    def set_status(new):
        nonlocal status, last_save
        if new != status:
            on_status_change(status, new)
            status = new
            last_save = 0   # ���°� �ٲ�� ���� �ֱ⸦ ��ٸ��� �ʰ� �ٷ� ���

    def restart_calibration(why):
        nonlocal model, phase, good, bad, pct, bad_since, raw, filt, tries, temp_base, sm, rise_since
        log.info(f"{why} -> �ڼ� �н� �ٽ� ����")
        model, phase, good, bad, pct, bad_since, raw, filt = None, "wait", [], [], None, None, "����", OneEuro()
        tries, temp_base, sm, rise_since = 0, None, Smooth(cfg.get("smooth_sec", 0.25)), None
        recent.clear()
        set_status("����")

    try:
        cam_seq, face_id, pose_id = -1, 0, 0
        show_pose, neck_line = None, None   # ȭ�鿡 �׸� �ֽ� ���, ��-��� ��
        while running:
            if not camera.is_alive() or not face_thread.is_alive() or (pose_thread and not pose_thread.is_alive()):
                log.warning("ī�޶󡤾󱼡���� ������ �� �ϳ��� ���� -> �ٽ� ����")
                break
            if show or publisher is not None:   # ȭ���� ī�޶� �ӵ�(�ִ� camera_fps) �״�� �ε巴�� ����
                cam_seq, frame = camera.wait_new(cam_seq, 0.5)
                if frame is None:
                    continue
                fid, new_face, _ = face_thread.latest()
            else:      # â�� ������ �� �� ����� ���� ���� ����� CPU�� �Ƴ�
                fid, new_face, _ = face_thread.wait_new(face_id, 0.5)

            # ������ ���� '���� ȭ��'���� ���� �󱼰� ����� ¦���� ��.
            # (����� �ʴ� 5��, ���� 30�� ����ؼ�, �ֽ� ������� ���� ���� ������ �� ���� �ٸ� ������ ����
            #  ���븸 ������ �͸� ���� ������ �� ��ó�� ����) -> ��� ����� ���� ���� ������ ����
            h, w = camera.shape
            new_face_result = fid != face_id
            if new_face_result:   # ���� �� �� ���󰡴� ����� �󱼸� (ȭ�鿡 �׸��� �� ���� �׻� �ֽ�)
                face_id, face_lm = fid, target.pick(new_face or [], w, h, time.monotonic())
            judge, pose_res, judge_face = False, None, face_lm
            if pose_thread is None:
                judge = new_face_result
            else:
                pid, res, stamp, pseq = pose_thread.latest_full()
                show_pose = res if res is not None and time.monotonic() - stamp < POSE_MAX_AGE else None
                if pid != pose_id:
                    pose_id, judge, pose_res = pid, True, res
                    faces = face_thread.find(pseq) or []   # ����� ���� ȭ���� �� (���󰡴� ��� �͸�)
                    judge_face = min(faces, key=lambda f: math.dist(Target._measure(f, w, h)[0], target.center),
                                     default=None) if target.center is not None and faces else face_lm
                    if judge_face is not None and target.center is not None and math.dist(
                            Target._measure(judge_face, w, h)[0], target.center) > max(3 * target.size, 0.15 * w):
                        judge_face = None
                elif new_face_result and time.monotonic() - stamp > POSE_MAX_AGE:
                    judge = True                         # ��� ����� �������� �󱼸�����

            if judge:   # ���� ��ü�� ��귮�� ���� ����
                now = time.monotonic()
                pose_lm = pose_res.pose_landmarks.landmark if pose_res and pose_res.pose_landmarks else None
                feats, reason = get_features(cv2, pose_lm, judge_face, w, h, cfg.get("camera_fov_deg", 65),
                                             cfg.get("use_shoulders", True))
                if judge_face is not None or (pose_lm is not None and now - target.seen < 1.0):
                    last_seen = now                      # ���󰡴� ����� ���� (�ٸ� ��� ���� ����)
                if target.lock_id != model_lock and reset_sec and phase != "wait":
                    restart_calibration("�ٸ� ������� �ٲ�")   # �� ����� ���� �н�
                model_lock = target.lock_id
                if feats is not None:
                    feats = prepare(sm, feats, now)
                    neck_line = neck_points(feats)
                    if phase == "run" and not can_judge(model, feats):
                        feats, reason = None, {"arms": "LOWER YOUR ARMS", "twist": "FACE THE CAMERA"}.get(
                            feats["sh_problem"], "MOVE BACK - show both shoulders")
                else:
                    neck_line = None

                # ���(��)�� ���̴µ� �󱼸� ������ ���(������ ���� ��): ���� ���̸� ��� ������ ��� ����
                hidden = feats is None and pose_lm is not None and phase == "run"
                if hidden and now - last_valid <= FACE_HIDDEN_HOLD:
                    sub = "face hidden - keeping last result" if judge_face is None else f"{reason} - keeping last result"
                elif feats is None:
                    text, sub, color = ("NO PERSON" if now - last_seen > 0.3 else reason), "", GRAY
                    if now - last_valid > (FACE_HIDDEN_HOLD if hidden else ABSENT_SEC):   # ���� �Ұ��� �̾����� �ڸ� ���
                        bad_since, raw = None, "����"
                        set_status("����")
                        recent.clear()                     # ���� ������ �����, ���ƿ��� �� ����� ��� ���� �ʰ�
                        filt, pct, rise_since = OneEuro(), None, None
                    # �н� �߿��� ���(3�� �̳�) �� ���̴� �� ��ٸ� (�׵����� ������ ����). ���� �� ���̸� ó������
                    if phase not in ("wait", "run") and now - last_valid > FACE_HIDDEN_HOLD:
                        log.info(f"�н� �� ����� {FACE_HIDDEN_HOLD}�� �Ѱ� �� ���� -> ó������ �ٽ�")
                        phase, good, bad, tries = "wait", [], [], 0
                    if model and reset_sec and now - last_seen > reset_sec:
                        restart_calibration("����� ����(�� ������ ���)")
                else:
                    if phase in ("good_rec", "bad_rec") and now - last_valid > 0.5:
                        phase_start += now - last_valid   # ��� �� ������ �ð���ŭ ���� �ð��� �÷� ��
                    last_valid = now
                    if phase == "wait":
                        phase, phase_start = "good_ready", now
                        log.info("��� ����, �ڼ� �н� ����")

                    # ---------- �ڼ� �н�: �ٸ� �ڼ� -> ���� �ڼ� ----------
                    if phase in ("good_ready", "bad_ready"):
                        left = READY_SEC - (now - phase_start)
                        step = "1/2  SIT UP STRAIGHT" if phase == "good_ready" else "2/2  NOW TURTLE NECK!"
                        text, color = f"{step}  {math.ceil(max(left, 0))}", YELLOW
                        sub = retry_msg if now < retry_msg_until \
                            else ("Sit tall, chin in" if phase == "good_ready"
                                  else "Push your head forward like usual bad posture")
                        if phase == "bad_ready" and temp_base is not None and now >= retry_msg_until:
                            sub += f"  (head forward {neck_offset(feats, temp_base)[0]:+.1f}cm)"
                        if left <= 0:
                            phase = "good_rec" if phase == "good_ready" else "bad_rec"
                            phase_start = now
                    elif phase in ("good_rec", "bad_rec"):
                        (good if phase == "good_rec" else bad).append(feats)
                        text = "1/2  HOLD STRAIGHT..." if phase == "good_rec" else "2/2  HOLD IT..."
                        sub, color = f"recording {max(cfg['calib_sec'] - (now - phase_start), 0):.1f}s", YELLOW
                        if phase == "bad_rec" and temp_base is not None:
                            sub += f"  (head forward {neck_offset(feats, temp_base)[0]:+.1f}cm)"
                        if now - phase_start >= cfg["calib_sec"]:
                            if phase == "good_rec":
                                phase, phase_start, bad, tries = "bad_ready", now, [], 0
                                temp_base = make_base(good)
                                log.info(f"�ٸ� �ڼ� ���� �Ϸ� ({len(good)}��, ��� ���: {'sw0' in temp_base})")
                            else:
                                tries += 1
                                model, sep, delta, noise = train(good, bad, force=tries >= MAX_TRIES)
                                log.info(f"�źϸ� ���� {tries}��°: �� �� {delta[0]:+.1f}cm, �Ʒ� {delta[1]:+.1f}cm, "
                                         f"��鸲 {noise:.1f}cm, ���� ���� {sep:.1f} -> {'����' if model else '����'}")
                                if model is None and tries >= MAX_TRIES:
                                    # �� ��°�� ���� -> �� �ݺ����� �ʰ� �⺻ �źϸ� ������ �н� (����� ���� ����)
                                    model = train_default(good)
                                    log.warning(f"�źϸ� �ڼ��� {MAX_TRIES}�� �� ����� �� �� -> �ٸ� �ڼ��� �״��, "
                                                f"�źϸ��� �⺻��(�� �� {DEFAULT_DELTA[0]}cm, �Ʒ� {DEFAULT_DELTA[1]}cm)���� �н�")
                                if model is None:   # ù ��°�� �������� ����: �� �� �� ��
                                    phase, phase_start, bad = "bad_ready", now, []
                                    retry_msg_until = now + READY_SEC
                                    retry_msg = (f"One more time: head moved only {math.hypot(*delta):.1f}cm - push it forward"
                                                 if math.hypot(*delta) < MIN_MOVE_CM else
                                                 "One more time: hold still while recording")
                                else:
                                    phase, filt = "run", OneEuro()
                                    log.info(f"�ڼ� �н� �Ϸ� ({'�⺻�� ���' if model.get('default') else f'���� ���� {sep:.1f}'}, "
                                             f"��� ���: {'sw0' in model}, "
                                             f"�źϸ� �� ���� ������ {model['delta'][0]:.1f}cm, �Ʒ��� {model['delta'][1]:.1f}cm)")
                                    if "sw0" not in model:
                                        log.warning("����� �� �� ������ ���� ���� ���� ���� -> ���� ���̸� �źϸ����� �� �� ����")
                                    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
                                        json.dump(model, f)

                    # ---------- �Ǻ� ----------
                    else:
                        recent.append(posture_score(model, feats))
                        # �ֱ� 3���� ��� �� -> �� �� Ƣ�� ���� ����, �״��� One Euro�� �ε巴��, 0~100%�� ����
                        new_pct = min(max(filt(statistics.median(recent), now), 0.0), 100.0)
                        if feats["sh_from_memory"] and pct is not None and new_pct > pct + 1:
                            rise_since = rise_since or now
                            if now - rise_since < MEMORY_TRUST_SEC:
                                new_pct = pct   # ����� ����δ� ������ 1�� �Ѱ� ���ƾ� �ø� (ª�� ��߳� ����)
                        else:
                            rise_since = None
                        pct = new_pct
                        raw = raw_status(pct, cfg, raw)
                        new_status, bad_since, duration = hold(raw, bad_since, cfg.get("danger_after_sec", 2.5), now)
                        set_status(new_status)
                        text, color = f"{STATUS_EN[status]}  {pct:.0f}%", STATUS_COLOR[status]
                        sub = "" if "sw0" not in model or feats["sh_use"] else "shoulders not visible"

                        shoulder, tilt = None, feats["tilt"]
                        if tilt is not None and "tilt" in model:
                            shoulder = "Ʋ����" if tilt - model["tilt"] >= cfg["shoulder_tilt_deg"] else "����"
                        if now - last_save >= cfg["save_interval"]:
                            hp = feats["pose"]
                            fwd, down, lean = neck_offset(feats, model)
                            log.info(f"{status} ���� {pct:.0f}% (�� ������ {fwd:+.1f}cm, �Ʒ��� {down:+.1f}cm, "
                                     f"���� ���� {lean:+.0f}��, ���� {hp['pitch']:+.0f}��, �Ÿ� {hp['dist']:.0f}cm, "
                                     f"��� {'���' if feats['sh_from_memory'] else ('���' if feats['sh_use'] else '�� ��')})")
                            threading.Thread(target=send, daemon=True, args=({
                                "user_id": cfg["user_id"],
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "worse_pct": round(pct, 1),
                                "status": status,
                                "shoulder_status": shoulder,
                                "shoulder_tilt": round(tilt, 1) if shoulder else None,
                                "bad_duration": round(duration, 1),
                            }, cfg["server_url"])).start()   # ��׶��� ����: ������ ������ ȭ���� �� ����
                            post_status(status)   # ��� �ִٴ� ��ȣ �� ���� ������
                            last_save = now

                fps_text = (f"cam {camera.rate.value:.0f} / screen {screen_rate.value:.0f} / "
                            f"face {face_thread.rate.value:.0f} / pose "
                            + (f"{pose_thread.rate.value:.0f} fps" if pose_thread else "off"))
                if now - last_fps_log >= 10:
                    log.info(f"ó�� �ӵ�: {fps_text}")
                    last_fps_log = now

            if show or publisher is not None:
                screen_rate.tick()
                shown_pct = pct if phase == "run" else None
                # �׸��� ���纻�� �׸� (�󱼡���� �����尡 ���� ȭ���� �д� ���� �� �־)
                if draw(cv2, mp, frame.copy(), show_pose, face_lm, text, color, sub, shown_pct, cfg,
                        fps_text, neck_line, publisher, show) == ord("c"):
                    if os.path.exists(BASELINE_FILE):
                        os.remove(BASELINE_FILE)
                    restart_calibration("c Ű �Է�")
    finally:
        if publisher is not None:
            publisher.close()
        stop_event.set()   # ī�޶󡤾󱼡���� ������ ��� ����
        for t in threads:
            t.join(timeout=3)
        if show:
            cv2.destroyAllWindows()


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    global STATUS_URL
    cfg = load_json(CONFIG_FILE)
    if cfg is None:
        log.error(f"���� ���� ���� �Ǵ� ���� ����: {CONFIG_FILE}")
        return
    STATUS_URL = cfg["server_url"].rsplit("/", 1)[0] + "/status"
    global CAMERA_TILT
    CAMERA_TILT = cfg.get("camera_tilt_deg", CAMERA_TILT)
    log.info("���α׷� ����")
    left = unsent_count()
    if left:
        log.info(f"�������� �� ���� ������ {left}�� ���� -> ���� ����Ǹ� �ڵ� ����")
    while running:
        try:
            run(cfg)
            for _ in range(2):   # �����尡 ���缭 ���� ���: 2�� ���� �ٽ� ����
                if running:
                    time.sleep(1)
        except Exception as e:
            log.exception(f"���� �߻�, 10�� �� �����: {e}")
            for _ in range(10):   # ��� �߿��� Ctrl+C �ٷ� �ݿ�
                if running:
                    time.sleep(1)
    log.info("���α׷� ����")


if __name__ == "__main__":
    main()