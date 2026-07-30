"""Broadcast the drone's real pose so RViz renders lidar data correctly."""

import math

import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped, TransformStamped
from nav_msgs.msg import Path
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Imu
from tf2_ros import TransformBroadcaster

GPS_TOPIC = '/Mavic_2_PRO/gps'
IMU_TOPIC = '/imu'
WORLD_FRAME = 'map'
BODY_FRAME = 'base_link'
PATH_MAX_POSES = 2000
PATH_MIN_STEP = 0.25


class PoseBroadcaster(Node):
    def __init__(self):
        super().__init__('mavic_pose_broadcaster')
        self._position = None
        self._orientation = None
        self._last_path_point = None
        self._announced = False

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(PointStamped, GPS_TOPIC, self._on_gps, qos)
        self.create_subscription(Imu, IMU_TOPIC, self._on_imu, qos)

        self._tf = TransformBroadcaster(self)
        self._pose_pub = self.create_publisher(PoseStamped, '/Mavic_2_PRO/pose', 10)
        self._path_pub = self.create_publisher(Path, '/Mavic_2_PRO/path', 10)

        self._path = Path()
        self._path.header.frame_id = WORLD_FRAME

        self.create_timer(0.02, self._publish)
        self.get_logger().info('Waiting for GPS and IMU...')

    def _on_gps(self, msg):
        self._position = (msg.point.x, msg.point.y, msg.point.z)

    def _on_imu(self, msg):
        q = msg.orientation
        if q.x == 0.0 and q.y == 0.0 and q.z == 0.0 and q.w == 0.0:
            return
        self._orientation = (q.x, q.y, q.z, q.w)

    def _publish(self):
        if self._position is None or self._orientation is None:
            return
        if not self._announced:
            self.get_logger().info('Both topics live. Broadcasting pose.')
            self._announced = True

        stamp = self.get_clock().now().to_msg()
        x, y, z = self._position
        qx, qy, qz, qw = self._orientation

        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = WORLD_FRAME
        t.child_frame_id = BODY_FRAME
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = z
        t.transform.rotation.x = qx
        t.transform.rotation.y = qy
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self._tf.sendTransform(t)

        pose = PoseStamped()
        pose.header.stamp = stamp
        pose.header.frame_id = WORLD_FRAME
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = z
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        self._pose_pub.publish(pose)

        if self._should_append(x, y, z):
            self._last_path_point = (x, y, z)
            self._path.poses.append(pose)
            if len(self._path.poses) > PATH_MAX_POSES:
                self._path.poses.pop(0)
            self._path.header.stamp = stamp
            self._path_pub.publish(self._path)

    def _should_append(self, x, y, z):
        if self._last_path_point is None:
            return True
        return math.dist((x, y, z), self._last_path_point) >= PATH_MIN_STEP


def main(args=None):
    rclpy.init(args=args)
    node = PoseBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
