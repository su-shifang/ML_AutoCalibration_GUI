import mlcolorimeter as mlcm
import os
import shutil
import time
from typing import List, Optional, Literal, Callable

"""
    field_curve.py is an example script that shows a simplified way to do vid scan, then get field curve
"""
MsgLevel = Literal["INFO", "WARN", "ERROR"]
FILE_COARSE_CSV = "coarse_result.csv"
FILE_COARSE_FIT_CSV = "coarse_fitResult.csv"
FILE_FINE_CSV = "fine_result.csv"
FILE_FINE_FIT_CSV = "fine_fitresult.csv"
DIR_COARSE_IMG = "coarse_images"
DIR_FINE_IMG = "fine_images"
MOTION_NAME = "CameraMotion"


def safe_copy_images(src_dir: str, dst_dir: str):
    if not os.path.exists(src_dir):
        return
    for filename in os.listdir(src_dir):
        src_path = os.path.join(src_dir, filename)
        if os.path.isfile(src_path):
            dst_path = os.path.join(dst_dir, filename)
            try:
                shutil.copy(src_path, dst_path)
            except OSError as e:
                raise RuntimeError(f"拷贝文件 {filename} 失败: {e}")


def safe_rename(src: str, dst: str):
    if not os.path.exists(src):
        return
    try:
        os.rename(src, dst)
    except OSError as e:
        raise RuntimeError(f"重命名文件 {src} 到 {dst} 失败: {e}")


def field_curve(
        colorimeter: mlcm.ML_Colorimeter,
        exposure: mlcm.pyExposureSetting,
        out_path: str,
        focus_config: mlcm.pyFocusScanConfig_ = None,
        freq_list: List[float] = [6.75, 13.5],
        binn_selector: mlcm.BinningSelector = mlcm.BinningSelector.Logic,
        binn_mode: mlcm.BinningMode = mlcm.BinningMode.AVERAGE,
        binn: mlcm.Binning = mlcm.Binning.ONE_BY_ONE,
        pixel_format: mlcm.MLPixelFormat = mlcm.MLPixelFormat.MLMono12,
        status_callback: Optional[Callable[[MsgLevel, str], None]] = None
):
    def update_status(level: MsgLevel, message: str):
        msg = f"[{level}] {message}"
        if status_callback is not None:
            try:
                status_callback(level, msg)
            except Exception:
                # 回调出错不中断采集，降级打印到控制台
                print(msg)
        else:
            print(msg)
    try:
        module_id = 1
        ml_mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
        # ---------------------- camera configuration -----------------
        ret = ml_mono.ml_set_binning_selector(binn_selector)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_binning_selector error, msg: {ret.message}")

        # Set binning mode for camera.
        ret = ml_mono.ml_set_binning_mode(binn_mode)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_binning_mode error, msg: {ret.message}")
        
        ret = ml_mono.ml_set_binning(binn)
        if not ret.success:
            raise RuntimeError(f"ml_set_binning error, msg: {ret.message}")

        # Format of the pixel to use for acquisition.
        ret = ml_mono.ml_set_pixel_format(pixel_format)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_pixel_format error, msg: {ret.message}")
        focus_scan = mlcm.pyMLFocusScan(mlcm.MLFocusScan(), ml_mono)

        # Set exposure for camera, contain auto and fixed.
        ret = ml_mono.ml_set_exposure(exposure)
        if not ret.success:
            raise RuntimeError(f"ml_set_exposure error, msg: {ret.message}")
        et=ml_mono.ml_get_exposure_time()
        update_status("INFO",f"相机参数设置完成，自动曝光结束，曝光时间：{str(et)}")

        for freq in freq_list:
            update_status(
                "INFO", f"====================start freq: {freq} auto focus====================")

            coarse_csv_src = os.path.join(out_path, FILE_COARSE_CSV)
            coarse_csv_dst = os.path.join(
                out_path, f"coarse_result_{str(freq)}.csv")
            coarse_csv_fit_src = os.path.join(out_path, FILE_COARSE_FIT_CSV)
            coarse_csv_fit_dst = os.path.join(
                out_path, f"coarse_fitresult_{str(freq)}.csv")
            coarse_image_src = os.path.join(out_path, DIR_COARSE_IMG)
            coarse_image_dst = os.path.join(
                out_path, f"coarse_images_{str(freq)}")

            # clear current freq result
            if os.path.exists(coarse_csv_dst):
                os.remove(coarse_csv_dst)
            if os.path.exists(coarse_csv_fit_dst):
                os.remove(coarse_csv_fit_dst)
            if os.path.exists(coarse_image_dst):
                # Clear the directory and its contents
                shutil.rmtree(coarse_image_dst)
            os.makedirs(coarse_image_dst, exist_ok=True)

            fine_csv_src = fine_csv_dst = fine_img_src = fine_img_dst = ""
            if focus_config.use_fine_adjust:
                fine_csv_src = os.path.join(out_path, FILE_FINE_CSV)
                fine_csv_dst = os.path.join(
                    out_path, f"fine_result_{str(freq)}.csv")
                fine_csv_fit_src = os.path.join(out_path, FILE_FINE_FIT_CSV)
                fine_csv_fit_dst = os.path.join(
                    out_path, f"fine_fitresult_{str(freq)}.csv")
                fine_img_src = os.path.join(out_path, DIR_FINE_IMG)
                fine_img_dst = os.path.join(
                    out_path, f"fine_images_{str(freq)}")
                if os.path.exists(fine_csv_dst):
                    os.remove(fine_csv_dst)
                if os.path.exists(fine_csv_fit_dst):
                    os.remove(fine_csv_fit_dst)
                if os.path.exists(fine_img_dst):
                    shutil.rmtree(fine_img_dst)
                os.makedirs(fine_img_dst, exist_ok=True)

            if focus_config.save_result_img:
                focus_config.image_save_path = out_path

            focus_config.freq = freq

            status = focus_scan.ml_start_focusscan()

            if not status:
                raise RuntimeError(
                    f"ml_start_focusscan error, msg: {ret.message}")

            ret = focus_scan.ml_focusscan_async(
                motion_name=MOTION_NAME, config=focus_config)
            if not ret.success:
                raise RuntimeError(
                    f"ml_focusscan_async error, msg: {ret.message}")

            ret = focus_scan.ml_wait_focusscan_finish()

            if ret.success:
                res = focus_scan.ml_get_focusscan_result()
                focus_scan.ml_get_combin_result()
                ret = focus_scan.ml_save_focusscan_result(out_path, "")
                if not ret.success:
                    raise RuntimeError(
                        f"ml_save_focusscan_result error, msg: {ret.message}")
                if not os.path.exists(coarse_csv_src):
                    raise RuntimeError("coarse csv file not exist")
                if (focus_config.save_result_img):
                    focus_scan.ml_wait_for_tasks_finish()
            else:
                raise RuntimeError("ml_wait_focusscan_finish error")

            # 先拷贝、重命名，最后删除源目录
            safe_rename(coarse_csv_src, coarse_csv_dst)
            safe_rename(coarse_csv_fit_src, coarse_csv_fit_dst)
            update_status(
                "INFO", f"vid scan finish for freq {str(freq)}, coarse csv saved to {coarse_csv_dst}")

            safe_copy_images(coarse_image_src, coarse_image_dst)

            # 拷贝完后清理源文件夹
            if os.path.exists(coarse_image_src):
                shutil.rmtree(coarse_image_src)

            if focus_config.use_fine_adjust:
                if not os.path.exists(fine_csv_src):
                    raise RuntimeError(f"频率{freq} 精扫结果文件缺失")
                safe_rename(fine_csv_src, fine_csv_dst)
                safe_rename(fine_csv_fit_src, fine_csv_fit_dst)
                update_status("INFO", f"频率 {freq:.2f} 精扫csv已重命名完成")
                safe_copy_images(fine_img_src, fine_img_dst)
                if os.path.exists(fine_img_src):
                    shutil.rmtree(fine_img_src)

            update_status(
                "INFO", f"====================freq{freq} end====================")
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg)
        raise


if __name__ == "__main__":
    # set mono module calibration configuration path
    eye1_path = r"D:\MLOptic\MLColorimeter\weilaixing\EYE1"
    out_path = r"E:\testout\field_curve"
    path_list = [
        eye1_path,
    ]
    try:
        # create a ML_Colorimeter system instance
        ml_colorimeter = mlcm.ML_Colorimeter()
        # add mono module into ml_colorimeter system, according to path_list create one or more mono module
        ret = ml_colorimeter.ml_add_module(path_list=path_list)
        if not ret.success:
            raise RuntimeError("ml_add_module error")
        # connect all module in the ml_colorimeter system
        ret = ml_colorimeter.ml_connect()
        if not ret.success:
            raise RuntimeError("ml_connect error")
        exposure = mlcm.pyExposureSetting(
            exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100)
        roi_list = [
            mlcm.pyCVRect(5609, 3553, 500, 500),
            mlcm.pyCVRect(6199, 4297, 500, 500),
            mlcm.pyCVRect(5609, 4865, 500, 500),
            mlcm.pyCVRect(4908, 4353, 500, 500),
        ]
        freq_list = [6.75, 13]
        focus_config = mlcm.pyFocusScanConfig_(
            focus_max=12,
            focus_min=8,
            inf_position=21.46,
            focal_length=50.08,
            pixel_size=0.00345,
            focal_space=0,
            coarse_step=0.2,
            use_fine_adjust=True,
            fine_step=0.05,
            roi_list=roi_list,
            use_checkboard=True,
            use_lpmm_unit=False,
            save_result_img=True,
            average_count=3
        )

        field_curve(
            colorimeter=ml_colorimeter,
            exposure=exposure,
            out_path=out_path,
            focus_config=focus_config,
            freq_list=freq_list
        )
        print("✅ 全部线对场曲扫描执行完成! 结果路径: ", out_path)
    except Exception as e:
        print("❌ 程序异常终止：")
        print(e)
