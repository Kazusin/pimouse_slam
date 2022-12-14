#!/usr/bin/env python
#encoding: utf8
import sys, rospy, math, tf #add tf(TransformBroadcaster)
from pimouse_ros.msg import MotorFreqs
from geometry_msgs.msg import Twist, Quaternion, TransformStamped, Point
#Question以下を追加
from std_srvs.srv import Trigger, TriggerResponse
from pimouse_ros.srv import TimedMotion                                               #追加
from nav_msgs.msg import Odometry                                                   #追加

class Motor():
    def __init__(self):
        if not self.set_power(False): sys.exit(1)   #モータの電源を切る（TrueをFalseに）

        rospy.on_shutdown(self.set_power)
        self.sub_raw = rospy.Subscriber('motor_raw', MotorFreqs, self.callback_raw_freq) #sub_rawはrospyというclassの中でSubscriberという処理をする
        self.sub_cmd_vel = rospy.Subscriber('cmd_vel', Twist, self.callback_cmd_vel) #名前、型、トピックを受信した際に呼び出す関数
        self.srv_on = rospy.Service('motor_on', Trigger, self.callback_on) #callback_onという関数をサービスを受けたときに呼び出す
        self.srv_off = rospy.Service('motor_off', Trigger, self.callback_off)
        self.srv_tm = rospy.Service('timed_motion', TimedMotion, self.callback_tm)    #追加
        self.last_time = rospy.Time.now()
        self.using_cmd_vel = False

        ###以下追加###

        self.pub_odom = rospy.Publisher('odom', Odometry, queue_size=10) #第三項はトピックを記録できるサイズが10までであること
        self.bc_odom = tf.TransformBroadcaster()

        self.x, self.y, self.th = 0.0, 0.0, 0.0
        self.vx, self.vth = 0.0, 0.0

        self.cur_time = rospy.Time.now() #いまの時間を記録
        self.last_time = self.cur_time #時間を上書き

        ##############

    def set_power(self,onoff=False):
        en = "/dev/rtmotoren0"
        try:
            with open(en,'w') as f:
                f.write("1\n" if onoff else "0\n")
            self.is_on = onoff
            return True
        except:
            rospy.logerr("cannot write to " + en)

        return False

    def set_raw_freq(self,left_hz,right_hz):
        if not self.is_on:
            rospy.logerr("not enpowered")
            return

        try:
            with open("/dev/rtmotor_raw_l0",'w') as lf,\
                 open("/dev/rtmotor_raw_r0",'w') as rf:
                lf.write(str(int(round(left_hz))) + "\n")
                rf.write(str(int(round(right_hz))) + "\n")
        except:
            rospy.logerr("cannot write to rtmotor_raw_*")

    def callback_raw_freq(self,message):
        self.set_raw_freq(message.left_hz,message.right_hz)

    def callback_cmd_vel(self,message):
        ###以下追加###
        if not self.is_on:
            return
        self.vx = message.linear.x
        self.vth = message.angular.z
        ############

        forward_hz = 80000.0*message.linear.x/(9*math.pi)
        rot_hz = 400.0*message.angular.z/math.pi
        self.set_raw_freq(forward_hz-rot_hz, forward_hz+rot_hz)

        self.using_cmd_vel = True
        self.last_time = rospy.Time.now()

    def onoff_response(self,onoff):                                #以下3つのメソッドを追加
        d = TriggerResponse()
        d.success = self.set_power(onoff)
        d.message = "ON" if self.is_on else "OFF"
        return d

    def send_odom(self):
        self.cur_time = rospy.Time.now() #現在時刻を代入

        dt = self.cur_time.to_sec() - self.last_time.to_sec() #前回の処理からの時間を記録
        self.x += self.vx * math.cos(self.th) * dt #速度のX成分に時間をかけて現在のX方向の位置を記録
        self.y += self.vx * math.sin(self.th) * dt
        self.th += self.vth * dt #ロボットの向きの変化量を記録 dtが大きいと精度が悪くなる

        q = tf.transformations.quaternion_from_euler(0, 0, self.th) #self.tfを変数qに型を変更する
        self.bc_odom.sendTransform((self.x,self.y,0.0), q, self.cur_time,"base_link","odom") #sendTransformにより以上の計算結果を送る
        #base_link:子供フレーム ロボットの座標系
        #odom:親フレーム オドメトリ（道のり）を計算するためのグローバル座標系

        odom = Odometry()
        odom.header.stamp = self.cur_time
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"

        odom.pose.pose.position = Point(self.x,self.y,0)
        odom.pose.pose.orientation = Quaternion(*q)

        odom.twist.twist.linear.x = self.vx
        odom.twist.twist.linear.y = 0.0
        odom.twist.twist.angular.z = self.vth

        self.pub_odom.publish(odom)

        self.last_time = self.cur_time


    def callback_on(self,message): return self.onoff_response(True)
    def callback_off(self,message): return self.onoff_response(False)

    def callback_tm(self,message):
        if not self.is_on:
            rospy.logerr("not enpowered")
            return False

        dev = "/dev/rtmotor0"
        try:
            with open(dev,'w') as f:
                f.write("%d %d %d\n" %
                    (message.left_hz,message.right_hz,message.duration_ms))
        except:
            rospy.logerr("cannot write to " + dev)
            return False

        return True

if __name__ == '__main__':
    rospy.init_node('motors')
    m = Motor()

    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        m.send_odom() #odom:odometry 道のりを何かの方法で測った値
        rate.sleep()

# Copyright 2016 Ryuichi Ueda
# Released under the BSD License.
# To make line numbers be identical with the book, this statement is written here. Don't move it to the header.
