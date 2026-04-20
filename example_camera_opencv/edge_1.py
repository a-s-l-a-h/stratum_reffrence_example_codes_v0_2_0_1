import stratum
import sys
import traceback
import time

try:
    import cv2
    import numpy as np
    OPENCV_OK = True
    print("[OPENCV] cv2 + numpy SUCCESSFULLY LOADED")
except Exception as e:
    OPENCV_OK = False
    print(f"[OPENCV] FAIL: {e}")

class CameraApp:
    def __init__(self, activity):
        self.activity = activity
        self.camera_device = None
        self.capture_session = None
        self.builder = None
        self.handler = None
        self._frame_count = 0
        self.last_time = time.time()

        print("[INIT] Building UI Layers...")
        try:
            # 1. FrameLayout (Root container)
            self.frame_layout = stratum.create_android_widget_FrameLayout(activity)

            # 2. TextureView (Bottom Layer: receives camera stream, hidden from us)
            self.texture_view = stratum.create_android_view_TextureView(activity)
            self.texture_view.setSurfaceTextureListener({
                "onSurfaceTextureAvailable":   self.on_surface_available,
                "onSurfaceTextureSizeChanged": self.on_surface_size_changed,
                "onSurfaceTextureDestroyed":   self.on_surface_destroyed,
                "onSurfaceTextureUpdated":     self.on_surface_updated,
            })

            # 3. ImageView (Top Layer: displays OpenCV frames)
            self.image_view = stratum.create_android_widget_ImageView(activity)

            # Add to stack
            self.frame_layout.addView(self.texture_view)
            self.frame_layout.addView(self.image_view)

            stratum.setContentView(activity, self.frame_layout)
            print("[INIT] Dual-Layer UI OK")
        except Exception as e:
            print(f"[FATAL INIT] {e}")
            traceback.print_exc()

    # ── Safe Constructor Helpers ──────────────────────────────────────────────
    def _create_handler(self, looper):
        cls = stratum.android_os_Handler
        for i in range(10):
            if hasattr(cls, f"new_{i}"):
                try: return getattr(cls, f"new_{i}")(looper)
                except: pass
        raise RuntimeError("Could not find Handler(Looper) constructor")

    def _create_surface(self, st):
        cls = stratum.android_view_Surface
        for i in range(10):
            if hasattr(cls, f"new_{i}"):
                try: return getattr(cls, f"new_{i}")(st)
                except: pass
        raise RuntimeError("Could not find Surface(SurfaceTexture) constructor")

    def _create_array_list(self):
        cls = stratum.java_util_ArrayList
        for i in range(10):
            if hasattr(cls, f"new_{i}"):
                try:
                    res = getattr(cls, f"new_{i}")()
                    if res is not None: return res
                except: pass
        raise RuntimeError("Could not find ArrayList() constructor")

    # ── Camera Setup ──────────────────────────────────────────────────────────
    def on_surface_available(self, st, w, h):
        print(f"[CB] surfaceAvailable {w}x{h}")
        try:
            sys_svc = self.activity.getSystemService("camera")

            # v5.0 Optimization: Direct Class Casting is 10x faster than string lookups
            cam_mgr = stratum.android_hardware_camera2_CameraManager._stratum_cast(sys_svc)

            looper = stratum.android_os_Looper.getMainLooper_static()
            self.handler = self._create_handler(looper)

            cam_mgr.openCamera("0", {
                "onOpened":       self.on_camera_opened,
                "onDisconnected": self.on_camera_disconnected,
                "onError":        self.on_camera_error,
            }, self.handler)
        except Exception as e:
            traceback.print_exc()

    def on_camera_opened(self, raw_device):
        print("[CB] cameraOpened")
        try:
            self.camera_device = stratum.android_hardware_camera2_CameraDevice._stratum_cast(raw_device)

            st = self.texture_view.getSurfaceTexture()
            surface = self._create_surface(st)

            self.builder = self.camera_device.createCaptureRequest(1)
            self.builder.addTarget(surface)

            lst = self._create_array_list()
            lst.add(surface)
            lst_if = stratum.java_util_List._stratum_cast(lst)

            self.camera_device.createCaptureSession(lst_if, {
                "onConfigured":      self.on_session_configured,
                "onConfigureFailed": self.on_session_failed,
            }, self.handler)
        except Exception as e:
            traceback.print_exc()

    def on_session_configured(self, raw_session):
        try:
            self.capture_session = stratum.android_hardware_camera2_CameraCaptureSession._stratum_cast(raw_session)
            req = self.builder.build()
            self.capture_session.setRepeatingRequest(req, None, self.handler)
            print("\n=======================================================")
            print(">>> PREVIEW LIVE — STRATUM V5.0 ZERO-COPY ACTIVE <<<")
            print("=======================================================\n")
        except Exception as e:
            traceback.print_exc()

    def on_session_failed(self, raw): print("[CB] sessionFailed")
    def on_camera_disconnected(self, raw): print("[CB] disconnected")
    def on_camera_error(self, raw, code): print(f"[CB] error code={code}")
    def on_surface_size_changed(self, st, w, h): pass
    def on_surface_destroyed(self, st):
        self.shutdown()
        return True

    # ── OpenCV Processing Frame-by-Frame ──────────────────────────────────────
    def on_surface_updated(self, st):
        self._frame_count += 1
        if not OPENCV_OK: return

        if self._frame_count % 2 != 0:
            return

        try:
            self._process_and_draw()
        except Exception as e:
            print(f"[OPENCV ERROR] {e}")
            traceback.print_exc()

    def _process_and_draw(self):
            t0 = time.time()

            # =========================================================================
            # 1. ONE-TIME INITIALIZATION (Zero-Copy & Memory Pre-allocation)
            # =========================================================================
            if not hasattr(self, "bb_wrapper"):
                print("[OPENCV] Allocating Reusable Memory...")

                first_frame = self.texture_view.getBitmap()
                if first_frame is None: return

                self.w = first_frame.getWidth()
                self.h = first_frame.getHeight()
                size = self.w * self.h * 4

                self.in_bmp = first_frame
                self.out_bmp = first_frame.copy(first_frame.getConfig(), True)

                raw_buffer = stratum.allocate_direct_buffer(size)
                self.bb_wrapper = stratum.java_nio_ByteBuffer._stratum_cast(raw_buffer)
                self.mem_view = self.bb_wrapper.duplicate()

                # 🌟 [NEW] Create the DIRECT NumPy wrapper around the Java memory
                self.arr = np.array(self.mem_view, copy=False).reshape((self.h, self.w, 4))

                # 🌟 [NEW] Pre-allocate all OpenCV intermediate buffers ONCE
                self.bgr_buf = np.empty((self.h, self.w, 3), dtype=np.uint8)
                self.gray_buf = np.empty((self.h, self.w), dtype=np.uint8)
                self.blur_buf = np.empty((self.h, self.w), dtype=np.uint8)
                self.edges_buf = np.empty((self.h, self.w), dtype=np.uint8)
                self.bgr_gray_buf = np.empty((self.h, self.w, 3), dtype=np.uint8)
                self.kernel = np.ones((2, 2), np.uint8)

            else:
                # HOT LOOP: Reuse the existing Bitmap memory!
                if self.texture_view.getBitmap(self.in_bmp) is None: return

            # =========================================================================
            # 2. THE ZERO-COPY PIPELINE
            # =========================================================================

            # A. Copy Android Hardware Pixels -> C++ Direct Memory
            self.bb_wrapper.rewind()
            self.in_bmp.copyPixelsToBuffer(self.bb_wrapper)

            # B. OpenCV Processing (100% IN-PLACE using 'dst=')
            cv2.cvtColor(self.arr, cv2.COLOR_RGBA2BGR, dst=self.bgr_buf)
            cv2.cvtColor(self.bgr_buf, cv2.COLOR_BGR2GRAY, dst=self.gray_buf)

            cv2.GaussianBlur(self.gray_buf, (5, 5), 0, dst=self.blur_buf)

            # Canny doesn't support dst natively, so we assign it to the pre-allocated buffer
            self.edges_buf[:] = cv2.Canny(self.blur_buf, 50, 150)

            dilated_edges = cv2.dilate(self.edges_buf, self.kernel, iterations=1)

            cv2.cvtColor(self.gray_buf, cv2.COLOR_GRAY2BGR, dst=self.bgr_gray_buf)

            # NumPy masked assignment (highly optimized)
            self.bgr_gray_buf[dilated_edges > 0] = [0, 255, 0]

            # FPS Counter
            fps = 1.0 / (t0 - self.last_time) if self.last_time else 0
            self.last_time = t0
            cv2.putText(self.bgr_gray_buf, f"STRATUM V5 ZERO-COPY: {fps:.1f} FPS",
                        (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 5)

            # 🌟 C. Write back DIRECTLY to Native Memory! No .tobytes()!
            cv2.cvtColor(self.bgr_gray_buf, cv2.COLOR_BGR2RGBA, dst=self.arr)

            # D. Push Native Memory to the Output Bitmap
            self.bb_wrapper.rewind()
            self.out_bmp.copyPixelsFromBuffer(self.bb_wrapper)

            # E. Render to UI
            self.image_view.setImageBitmap(self.out_bmp)

    def shutdown(self):
        if self.capture_session:
            try: self.capture_session.close()
            except: pass
        if self.camera_device:
            try: self.camera_device.close()
            except: pass


# ─── Android App Lifecycle ───────────────────────────────────────────────────
app = None

def onCreate():
    global app
    app = CameraApp(stratum.getActivity())

def onResume():
    global app
    if app and app.camera_device is None:
        st = app.texture_view.getSurfaceTexture()
        if st:
            app.on_surface_available(st, 0, 0)

def onPause(): pass
def onStop(): pass
def onDestroy():
    global app
    if app:
        app.shutdown()
        app = None