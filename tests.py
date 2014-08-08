# test module for the framework

from proxycachingevalfw import *
import unittest
import time

@PacketTimer('request', 'receivedCallback')
class TimedPeer(Peer):
	block = None


class TestRequestResponse(unittest.TestCase):

	def setUp(self):
		self.c1 = Peer(1001, "c1")
		self.c2 = Peer(1002, "c2")
		self.c3 = Peer(1003, "c3")
		self.p = ForwardProxy(0, "Proxy")

		self.c1.connectTo(self.p).setLag(0.1)
		self.p.connectTo(self.c1).setLag(0.1)

		self.c3.connectTo(self.p).setLag(0.1)
		self.p.connectTo(self.c3).setLag(0.1)

	def test_requests(self):
		self.c1.request("lol")
		self.c3.request("pouet")

		time.sleep(1)

		self.assertEqual(self.c1.receivedData['payload'], 'There you go: lol')
		self.assertEqual(self.c3.receivedData['payload'], 'There you go: pouet')

class TestTiming(unittest.TestCase):

	def setUp(self):
		self.c1 = TimedPeer(1001, "c1")
		self.c2 = TimedPeer(1002, "c2")
		self.c3 = TimedPeer(1003, "c3")
		self.p = ForwardProxy(0, "Proxy")

		self.c1.connectTo(self.p).setLag(1)
		self.p.connectTo(self.c1).setLag(1)

		self.c3.connectTo(self.p).setLag(0.5)
		self.p.connectTo(self.c3).setLag(0.5)

	def test_basic_timing(self):
		self.c1.request("lol")
		self.c3.request("pouet")

		time.sleep(4)

		self.assertTrue(self.c1.latencies[0] > 2 and self.c1.latencies[0] < 3)

	def test_queue(self):
		# by sending two requests one right after the other and having a latency of 1/1
		# the first request should take 1+1 sec and the second 1+(1+1) as it has to wait for
		# the first to be sent
		self.c1.request("lol")
		self.c1.request("pouet")

		time.sleep(5)

		self.assertTrue(self.c1.latencies[0] > 2 and self.c1.latencies[0] < 3)
		self.assertTrue(self.c1.latencies[1] > 3 and self.c1.latencies[0] < 4)

class TestVideoServer(unittest.TestCase):

	def setUp(self):
		# testing direct access to a video server
		self.s2 = VideoServer(2, "s2")
		self.c4 = Client(1004, "c4")

		# we set the chunk to a big size so that we can determine accurately the download time
		self.c4.connectTo(self.s2).setLag(0.1).setBandwidth(2048).setMaxChunk(32000)
		self.s2.connectTo(self.c4).setLag(0.1).setBandwidth(2048).setMaxChunk(32000)

		self.video = {'idVideo': 1337, 'duration': 60, 'size': 2048, 'bitrate': 2048/60, 'title': 'Video', 'description': 'A video'}

	def test_video_access(self):
		self.s2.addVideo(video=self.video)
		self.c4.requestMedia(1337, 2)

		time.sleep(2)

		self.assertEqual(self.c4.receivedData['payload'], self.video)

		time.sleep(10)

	def test_add_video_access(self):
		self.s2.addVideo(60, 2048, 2048/60, 'Video', 'A video', 1337)
		self.c4.requestMedia(1337, 2)

		time.sleep(2)

		self.assertEqual(self.c4.receivedData['payload'], self.video)

	def test_transfer_speed(self):
		bigvideo = {'idVideo': 1, 'duration': 60, 'size': 8192, 'bitrate': 8192/60, 'title': 'Big Video', 'description': 'Big bitrate'}
		self.s2.addVideo(video=bigvideo)
		self.c4.requestMedia(1, 2)

		time.sleep(5)
		# should take 4.2 seconds, latency is 0.1, so 2*0.1, the size 8192 divided by the speed 2048: 2*0.1+8192/2048 = 4.2
		self.assertTrue(self.c4.latencies[0] > 4 and self.c4.latencies[0] < 5)

		bigvideo = {'idVideo': 2, 'duration': 60, 'size': 16384, 'bitrate': 8192/60, 'title': 'Big big Video', 'description': 'Biiiig bitrate'}
		self.s2.addVideo(video=bigvideo)
		self.c4.requestMedia(2, 2)

		time.sleep(9)
		# should take two times as much as it is two times as big
		self.assertTrue(self.c4.latencies[1] > 8 and self.c4.latencies[1] < 9)

class TestForwardProxy(unittest.TestCase):

	def setUp(self):
		self.c1 = Client(1001, "c1")
		self.c2 = Client(1002, "c2")
		self.c3 = Client(1003, "c3")
		self.p = ForwardProxy(0, "Proxy")

		self.c1.connectTo(self.p).setLag(0.1).setBandwidth(12000)
		self.p.connectTo(self.c1).setLag(0.1).setBandwidth(12000)

		self.c2.connectTo(self.p).setLag(0.1).setBandwidth(12000)
		self.p.connectTo(self.c2).setLag(0.1).setBandwidth(12000)

		self.c3.connectTo(self.p).setLag(0.1).setBandwidth(12000)
		self.p.connectTo(self.c3).setLag(0.1).setBandwidth(12000)

		self.s1 = VideoServer(1, "s1")

		self.s1.connectTo(self.p).setLag(0.01).setBandwidth(12000)
		self.p.connectTo(self.s1).setLag(0.01).setBandwidth(12000)

		self.video1 = {'idVideo': 1337, 'duration': 60, 'size': 2048, 'bitrate': 2048/60, 'title': 'Video', 'description': 'A video'}
		self.video2 = {'idVideo': 9001, 'duration': 55, 'size': 2000, 'bitrate': 2000/55, 'title': 'Video 2', 'description': 'Another video'}

	def test_one_video_access(self):
		self.s1.addVideo(video=self.video2)

		self.c1.requestMedia(9001, 1)

		time.sleep(2)

		self.assertEqual(self.c1.receivedData['payload'], self.video2)

	def test_multiple_video_multiple_access(self):
		self.s1.addVideo(video=self.video1)
		self.s1.addVideo(video=self.video2)

		self.c1.requestMedia(9001, 1)

		time.sleep(2)

		self.assertEqual(self.c1.receivedData['payload'], self.video2)

		self.c2.requestMedia(9001, 1)
		self.c3.requestMedia(1337, 1)

		time.sleep(2)

		self.assertEqual(self.c2.receivedData['payload'], self.video2)
		self.assertEqual(self.c3.receivedData['payload'], self.video1)

class TestUnlimitedProxy(unittest.TestCase):

	def setUp(self):
		self.c1 = Client(1001, "c1")
		self.c2 = Client(1002, "c2")
		self.p = UnlimitedProxy(0, "Proxy")

		#good bandwidth between the clients and proxy
		self.c1.connectTo(self.p).setLag(0.1).setBandwidth(12000)
		self.p.connectTo(self.c1).setLag(0.1).setBandwidth(12000)

		self.c2.connectTo(self.p).setLag(0.1).setBandwidth(12000)
		self.p.connectTo(self.c2).setLag(0.1).setBandwidth(12000)

		self.s1 = VideoServer(1, "s1")

		#but congested link between proxy and video server
		self.s1.connectTo(self.p).setLag(0.01).setBandwidth(1024)
		self.p.connectTo(self.s1).setLag(0.01).setBandwidth(1024)

		self.video1 = {'idVideo': 1337, 'duration': 60, 'size': 2048, 'bitrate': 2048/60, 'title': 'Video', 'description': 'A video'}
		self.bigvideo = {'idVideo': 1, 'duration': 60, 'size': 8192, 'bitrate': 8192/60, 'title': 'Big Video', 'description': 'Big bitrate'}

	def test_caching_benefits(self):
		self.s1.addVideo(video=self.video1)

		self.c1.requestMedia(1337, 1)

		time.sleep(3)

		self.c1.requestMedia(1337, 1)

		time.sleep(1)

		self.assertTrue(self.c1.latencies[0] > self.c1.latencies[1])


if __name__ == '__main__':
    unittest.main()
