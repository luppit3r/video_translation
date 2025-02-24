from moviepy.video.io.VideoFileClip import VideoFileClip

video = VideoFileClip("4.SW-belki-cz2/output/test.mp4")
print(f"Video duration: {video.duration} seconds")
video.close()