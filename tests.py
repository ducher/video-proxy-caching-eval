# test module for the framework

from model import *
from metrics import *
import simu
import unittest
import time

@PacketTimer('request', 'received_callback')
class TimedPeer(Peer):
    def __method(self):
        print("method")

    def method(self):
        self.__method()

@TwoMethodsTimerAndCounter("request_media", "start_playback", "_video_stopped")
class StopClient(Client):
    pass

@TwoMethodsTimer("request_media", "start_playback")
class LatenciesClient(Client):
    pass

class TestSimuHelpers(unittest.TestCase):

    def test_sleep(self):
        start = time.time()
        speed = config.speed
        simu.sleep(5)
        end = (time.time() - start) * speed
        self.assertAlmostEqual(end, 5, 1)

    def test_no_active_download(self):
        self.s1 = VideoServer(1, "s1")
        self.c1 = LatenciesClient(1001, "c1")
        self.c1.set_func_new_dl(simu.inc_nb_dl)
        self.c1.set_func_end_dl(simu.dec_nb_dl)
        
        self.c2 = LatenciesClient(1002, "c2")
        self.c2.set_func_new_dl(simu.inc_nb_dl)
        self.c2.set_func_end_dl(simu.dec_nb_dl)

        # we set the chunk to a big size so that we can determine accurately the download time
        self.c1.connect_to(self.s1).set_lag(0.1).set_bandwidth(1024).set_max_chunk(32)
        self.s1.connect_to(self.c1).set_lag(0.1).set_bandwidth(1024).set_max_chunk(32)

        self.video = {'idVideo': 1337, 'duration': 60, 'size': 2048, 'bitrate': 2048/60, 'title': 'Video', 'description': 'A video'}
        self.s1.add_video(video=self.video)

        self.c1.request_media(1337, 2)

        self.assertFalse(simu.no_active_download((self.c1, self.c2)))

        simu.sleep(3)

        self.assertTrue(simu.no_active_download((self.c1, self.c2)))



class TestRequestResponse(unittest.TestCase):

    def setUp(self):
        self.c1 = Peer(1001, "c1")
        self.c2 = Peer(1002, "c2")
        self.c3 = Peer(1003, "c3")
        self.p = ForwardProxy(0, "Proxy")

        self.c1.connect_to(self.p).set_lag(0.1)
        self.p.connect_to(self.c1).set_lag(0.1)

        self.c3.connect_to(self.p).set_lag(0.1)
        self.p.connect_to(self.c3).set_lag(0.1)

    def test_requests(self):
        self.c1.request("lol")
        self.c3.request("pouet")

        simu.sleep(1)

        self.assertEqual(self.c1.received_data['payload'], 'There you go: lol')
        self.assertEqual(self.c3.received_data['payload'], 'There you go: pouet')

class TestClient(unittest.TestCase):

    def setUp(self):
        # testing direct access to a video server
        self.s2 = VideoServer(2, "s2")
        self.c4 = StopClient(1004, "c4")

        # we set the chunk to a big size so that we can determine accurately the download time
        self.c4.connect_to(self.s2).set_lag(0.1).set_bandwidth(2048)
        self.s2.connect_to(self.c4).set_lag(0.1).set_bandwidth(2048)


        self.c1 = StopClient(1001, "c1")
        self.c2 = StopClient(1002, "c2")
        self.p = ForwardProxy(0, "Proxy")
        self.s1 = VideoServer(1, "s1")

        self.c1.connect_to(self.p).set_lag(0.1).set_bandwidth(2048)
        self.p.connect_to(self.c1).set_lag(0.1).set_bandwidth(2048)

        self.c2.connect_to(self.p).set_lag(0.1).set_bandwidth(2048)
        self.p.connect_to(self.c2).set_lag(0.1).set_bandwidth(2048)

        self.s1.connect_to(self.p).set_lag(0.01).set_bandwidth(1024)
        self.p.connect_to(self.s1).set_lag(0.01).set_bandwidth(1024)

    def test_buffer_big_bitrate(self):
        bigvideo = {'idVideo': 1, 'duration': 100, 'size': 409600, 'bitrate': 4096, 'title': 'Big Video', 'description': 'Big bitrate'}
        self.s2.add_video(video=bigvideo)
        self.c4.request_media(1, 2)

        self.c4.start_video_consumer()

        simu.sleep(2)

        #self.assertEqual(self.c4.received_data['payload'], self.video)

        simu.sleep(2)
        simu.sleep(2)
        simu.sleep(2)
        #print(str(self.c4.counter))
        self.assertGreater(self.c4.counter, 0)

    def test_wait_vs_nowait(self):
        bigvideo = {'idVideo': 1, 'duration': 10, 'size': 40960, 'bitrate': 4096, 'title': 'Big Video', 'description': 'Big bitrate'}
        self.s2.add_video(video=bigvideo)

        self.c4.set_buffer_size(6144)
        self.c4.start_video_consumer()

        self.c4.set_play_wait_buffer(False)
        self.c4.request_media(1, 2)
        simu.sleep(10)
        print(str(self.c4.counter))
        counter1 = self.c4.counter

        self.c4.set_play_wait_buffer(True)
        self.c4.request_media(1, 2)
        simu.sleep(10)
        print(str(self.c4.counter))
        counter2 = self.c4.counter - counter1

        self.assertGreater(counter1, counter2)



    def test_two_videos_buffer_nowait(self):
        video1 = {'idVideo': 1, 'duration': 10, 'size': 7680, 'bitrate': 768, 'title': 'Video', 'description': 'A video'}
        video2 = {'idVideo': 2, 'duration': 5, 'size': 7500, 'bitrate': 1500, 'title': 'Video', 'description': 'A video'}

        self.s1.add_video(video=video1)
        self.s1.add_video(video=video2)
        self.c2.set_play_wait_buffer(False)
        self.c1.set_play_wait_buffer(False)

        self.c2.start_video_consumer()
        self.c1.start_video_consumer()

        self.c1.request_media(1, 1)
        self.assertEqual(self.c1.counter, 0)
        simu.sleep(2)
        self.c2.request_media(2, 1)
        simu.sleep(10)
        #print(str(self.c2.counter))
        #print(str(self.c1.counter))
        self.assertGreater(self.c2.counter, 0)
        self.assertGreater(self.c1.counter, 0)

    def test_two_videos_buffer(self):
        video1 = {'idVideo': 1, 'duration': 10, 'size': 7680, 'bitrate': 768, 'title': 'Video', 'description': 'A video'}
        video2 = {'idVideo': 2, 'duration': 5, 'size': 7500, 'bitrate': 1500, 'title': 'Video', 'description': 'A video'}

        self.s1.add_video(video=video1)
        self.s1.add_video(video=video2)
        self.c2.set_play_wait_buffer(True)
        self.c1.set_play_wait_buffer(True)

        self.c2.start_video_consumer()
        self.c1.start_video_consumer()

        self.c1.request_media(1, 1)
        self.assertEqual(self.c1.counter, 0)
        simu.sleep(2)
        self.c2.request_media(2, 1)
        simu.sleep(10)
        #print(str(self.c2.counter))
        #print(str(self.c1.counter))
        self.assertGreater(self.c2.counter, 0)
        

        pass

class TestTiming(unittest.TestCase):

    def setUp(self):
        self.c1 = TimedPeer(1001, "c1")
        self.c2 = TimedPeer(1002, "c2")
        self.c3 = TimedPeer(1003, "c3")
        self.p = ForwardProxy(0, "Proxy")

        self.c1.connect_to(self.p).set_lag(1)
        self.p.connect_to(self.c1).set_lag(1)

        self.c3.connect_to(self.p).set_lag(0.5)
        self.p.connect_to(self.c3).set_lag(0.5)

    def test_basic_timing(self):
        self.c1.request("lol")
        self.c3.request("pouet")
        
        simu.sleep(4)

        self.assertTrue(self.c1.latencies[0] > 2 and self.c1.latencies[0] < 3)

    def test_queue(self):
        # by sending two requests one right after the other and having a latency of 1/1
        # the first request should take 1+1 sec and the second 1+(1+1) as it has to wait for
        # the first to be sent
        self.c1.request("lol")
        self.c1.request("pouet")

        simu.sleep(5)

        self.assertTrue(self.c1.latencies[0] > 2 and self.c1.latencies[0] < 3)
        self.assertTrue(self.c1.latencies[1] > 3 and self.c1.latencies[0] < 4)

    def test_wrapper(self):
        self.c1.method()

class TestVideoServer(unittest.TestCase):

    def setUp(self):
        # testing direct access to a video server
        self.s2 = VideoServer(2, "s2")
        self.c4 = LatenciesClient(1004, "c4")

        # we set the chunk to a big size so that we can determine accurately the download time
        self.c4.connect_to(self.s2).set_lag(0.1).set_bandwidth(2048).set_max_chunk(32000)
        self.s2.connect_to(self.c4).set_lag(0.1).set_bandwidth(2048).set_max_chunk(32000)

        self.video = {'idVideo': 1337, 'duration': 60, 'size': 2048, 'bitrate': 2048/60, 'title': 'Video', 'description': 'A video'}

    def test_video_access(self):
        self.s2.add_video(video=self.video)
        self.c4.request_media(1337, 2)

        simu.sleep(2)

        self.assertEqual(self.c4.received_data['payload'], self.video)

        simu.sleep(10)

    def test_add_video_access(self):
        self.s2.add_video(60, 2048, 2048/60, 'Video', 'A video', 1337)
        self.c4.request_media(1337, 2)

        simu.sleep(2)

        self.assertEqual(self.c4.received_data['payload'], self.video)

    def test_transfer_speed(self):
        bigvideo = {'idVideo': 1, 'duration': 60, 'size': 8192, 'bitrate': 8192/60, 'title': 'Big Video', 'description': 'Big bitrate'}
        self.s2.add_video(video=bigvideo)
        self.c4.set_buffer_size(8192)
        self.c4.request_media(1, 2)

        simu.sleep(5)
        print("Latency "+str(self.c4.latencies[0]))
        # should take 4.2 seconds, latency is 0.1, so 2*0.1, the size 8192 divided by the speed 2048: 2*0.1+8192/2048 = 4.2
        self.assertTrue(self.c4.latencies[0] > 4 and self.c4.latencies[0] < 5)

        bigvideo = {'idVideo': 2, 'duration': 60, 'size': 16384, 'bitrate': 8192/60, 'title': 'Big big Video', 'description': 'Biiiig bitrate'}
        self.s2.add_video(video=bigvideo)
        self.c4.request_media(2, 2)

        simu.sleep(9)
        # should take two times as much as it is two times as big
        self.assertTrue(self.c4.latencies[1] > 8 and self.c4.latencies[1] < 9)

class TestForwardProxy(unittest.TestCase):

    def setUp(self):
        self.c1 = Client(1001, "c1")
        self.c2 = Client(1002, "c2")
        self.c3 = Client(1003, "c3")
        self.p = ForwardProxy(0, "Proxy")

        self.c1.connect_to(self.p).set_lag(0.1).set_bandwidth(12000)
        self.p.connect_to(self.c1).set_lag(0.1).set_bandwidth(12000)

        self.c2.connect_to(self.p).set_lag(0.1).set_bandwidth(12000)
        self.p.connect_to(self.c2).set_lag(0.1).set_bandwidth(12000)

        self.c3.connect_to(self.p).set_lag(0.1).set_bandwidth(12000)
        self.p.connect_to(self.c3).set_lag(0.1).set_bandwidth(12000)

        self.s1 = VideoServer(1, "s1")

        self.s1.connect_to(self.p).set_lag(0.01).set_bandwidth(12000)
        self.p.connect_to(self.s1).set_lag(0.01).set_bandwidth(12000)

        self.video1 = {'idVideo': 1337, 'duration': 60, 'size': 2048, 'bitrate': 2048/60, 'title': 'Video', 'description': 'A video'}
        self.video2 = {'idVideo': 9001, 'duration': 55, 'size': 2000, 'bitrate': 2000/55, 'title': 'Video 2', 'description': 'Another video'}

    def test_one_video_access(self):
        self.s1.add_video(video=self.video2)

        self.c1.request_media(9001, 1)

        simu.sleep(2)

        self.assertEqual(self.c1.received_data['payload'], self.video2)

    def test_multiple_video_multiple_access(self):
        self.s1.add_video(video=self.video1)
        self.s1.add_video(video=self.video2)

        self.c1.request_media(9001, 1)

        simu.sleep(2)

        self.assertEqual(self.c1.received_data['payload'], self.video2)

        self.c2.request_media(9001, 1)
        self.c3.request_media(1337, 1)

        simu.sleep(2)

        self.assertEqual(self.c2.received_data['payload'], self.video2)
        self.assertEqual(self.c3.received_data['payload'], self.video1)

class TestUnlimitedProxy(unittest.TestCase):

    def setUp(self):
        self.c1 = LatenciesClient(1001, "c1")
        self.c2 = LatenciesClient(1002, "c2")
        self.p = UnlimitedProxy(0, "Proxy")

        #good bandwidth between the clients and proxy
        self.c1.connect_to(self.p).set_lag(0.1).set_bandwidth(12000)
        self.p.connect_to(self.c1).set_lag(0.1).set_bandwidth(12000)

        self.c2.connect_to(self.p).set_lag(0.1).set_bandwidth(12000)
        self.p.connect_to(self.c2).set_lag(0.1).set_bandwidth(12000)

        self.s1 = VideoServer(1, "s1")

        #but congested link between proxy and video server
        self.s1.connect_to(self.p).set_lag(0.01).set_bandwidth(1024)
        self.p.connect_to(self.s1).set_lag(0.01).set_bandwidth(1024)

        self.video1 = {'idVideo': 1337, 'duration': 60, 'size': 2048, 'bitrate': 2048/60, 'title': 'Video', 'description': 'A video'}
        self.bigvideo = {'idVideo': 1, 'duration': 60, 'size': 8192, 'bitrate': 8192/60, 'title': 'Big Video', 'description': 'Big bitrate'}

    def test_caching_benefits(self):
        self.s1.add_video(video=self.video1)
        self.c1.set_two_in_a_row_protection(False)

        self.c1.request_media(1337, 1)

        simu.sleep(3)

        self.c1.request_media(1337, 1)

        simu.sleep(2)

        self.c1.request_media(1337, 1)

        simu.sleep(2)

        print(self.c1.latencies)

        self.assertTrue(self.c1.latencies[0] > self.c1.latencies[1])


class TestFIFOProxy(unittest.TestCase):

    def setUp(self):
        self.c1 = LatenciesClient(1001, "c1")
        self.c2 = LatenciesClient(1002, "c2")
        self.p = FIFOProxy(0, "Proxy")

        #good bandwidth between the clients and proxy
        self.c1.connect_to(self.p).set_lag(0.1).set_bandwidth(12000)
        self.p.connect_to(self.c1).set_lag(0.1).set_bandwidth(12000)

        self.c2.connect_to(self.p).set_lag(0.1).set_bandwidth(12000)
        self.p.connect_to(self.c2).set_lag(0.1).set_bandwidth(12000)

        self.s1 = VideoServer(1, "s1")

        #but congested link between proxy and video server
        self.s1.connect_to(self.p).set_lag(0.01).set_bandwidth(1024)
        self.p.connect_to(self.s1).set_lag(0.01).set_bandwidth(1024)

        self.video1 = {'idVideo': 1337, 'duration': 60, 'size': 2048, 'bitrate': 2048/60, 'title': 'Video', 'description': 'A video'}
        self.bigvideo = {'idVideo': 1, 'duration': 60, 'size': 8192, 'bitrate': 8192/60, 'title': 'Big Video', 'description': 'Big bitrate'}

    def test_caching_benefits(self):
        self.s1.add_video(video=self.video1)

        self.c1.set_buffer_size(512)
        self.c2.set_buffer_size(512)

        self.c2.request_media(1337, 1)

        simu.sleep(3)

        self.c1.request_media(1337, 1)

        simu.sleep(2)

        self.assertTrue(self.c2.latencies[0] > self.c1.latencies[0])

    # def test_plot(self):
    #     video2 = {'idVideo': 9001, 'duration': 55, 'size': 2000, 'bitrate': 2000/55, 'title': 'Video 2', 'description': 'Another video'}

    #     self.s1.add_video(video=self.video1)
    #     self.s1.add_video(video=video2)
    #     self.s1.add_video(video=self.bigvideo)

    #     self.c1.request_media(1337, 1)

    #     simu.sleep(3)

    #     self.c1.request_media(1337, 1)
    #     self.c2.request_media(9001, 1)

    #     simu.sleep(3)

    #     self.c1.request_media(9001, 1)
    #     self.c2.request_media(1337, 1)

    #     simu.sleep(3)

    #     self.c1.request_media(1337, 1)
    #     simu.sleep(3)

    #     self.c1.request_media(1337, 1)
    #     simu.sleep(3)

    #     self.c1.request_media(1, 1)
    #     simu.sleep(5)
    #     self.c2.request_media(1, 1)
    #     simu.sleep(5)

    #     print(self.c1.latencies)

    #     ps = PlotStats()
    #     ps.plot_latencies(self.c1.latencies)
    #     ps.hist_latencies(self.c1.latencies+self.c2.latencies)

    def test_cache_stats(self):
        self.s1.add_video(video=self.video1)

        self.c2.request_media(1337, 1)
        # don't know why but when requesting with c1, it doesn't work.

        simu.sleep(3)

        self.c1.request_media(1337, 1)

        simu.sleep(1)

        stats = self.p.get_hit_stats()
        self.assertEqual(stats['byte_hit_ratio'], 0.5)
        self.assertEqual(stats['byte_cache'], self.video1['size']/8)


if __name__ == '__main__':
    unittest.main()
