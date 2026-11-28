import subprocess, sys, numpy as np, cv2
def detail(path, t):
    raw=subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',path,'-frames:v','1','-f','rawvideo','-pix_fmt','gray','-'],capture_output=True).stdout
    p=subprocess.run(['ffprobe','-v','error','-select_streams','v','-show_entries','stream=width,height','-of','csv=p=0',path],capture_output=True,text=True).stdout.strip().split(',')
    w,h=int(p[0]),int(p[1]); g=np.frombuffer(raw,np.uint8)[:w*h].reshape(h,w).astype(np.float32)
    # energy kept vs lost when bounced through half res: tiny loss = upscaled/soft source
    half=cv2.resize(cv2.resize(g,(w//2,h//2),interpolation=cv2.INTER_AREA),(w,h),interpolation=cv2.INTER_CUBIC)
    return np.sqrt(((g-half)**2).mean()), w, h
for p in sys.argv[1:]:
    d=[detail(p,t)[0] for t in (1.5,4,7)]
    print(f"{p.split('/')[-1]:22s} hf-detail {np.mean(d):5.2f}")
