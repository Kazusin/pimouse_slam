#!/usr/bin/env python
# coding:utf-8
import rospy
from geometry_msgs.msg import Twist 
from std_srvs.srv import Trigger, TriggerResponse #.srvファイルはサービスを用いるために使う

rospy.wait_for_service('/motor_on') #/motor_onというノードの処理を待つ
rospy.wait_for_service('/motor_off')
rospy.on_shutdown(rospy.ServiceProxy('/motor_off',Trigger).call)
rospy.ServiceProxy('/motor_on',Trigger).call() #サービスのハンドラを取得する

rospy.init_node('keyboard_cmd_vel')
pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
while not rospy.is_shutdown(): #シャットダウンされていないとき
	vel = Twist() #Twistというオブジェクトを生成する
	direction = raw_input('k: forward,  j: backward, h: left, l: right, return: stop > ')
	if 'k' in direction: vel.linear.x = 0.15
	if 'j' in direction: vel.linear.x = -0.15
	if 'h' in direction: vel.angular.z = 3.14/4  #pi/4[rad/s]
	if 'l' in direction: vel.angular.z = -3.14/4
	print vel 
	pub.publish(vel) #velを出力する