import mlcolorimeter as mlcm
import cv2
from typing import List, Literal, Optional, Callable
from datetime import datetime
import os
MsgLevel = Literal["INFO", "WARN", "ERROR"]


"""
    center_fit.py is an example script that shows a simplified way to fit rx cross center with circle.
"""


def datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]


def circle_fit_online(
        colorimeter: mlcm.ML_Colorimeter,
        nd_list: List[mlcm.MLFilterEnum],
        xyz_list: List[mlcm.MLFilterEnum],
        binn: mlcm.Binning,
        pixel_format: mlcm.MLPixelFormat,
        cyl_list: List[float],
        axis_list: List[int],
        roi: mlcm.pyCVRect,
        fit_file_path: str,
        out_path: str,
        status_callback: Optional[Callable[[MsgLevel, str], None]] = None
):
    run_time_tag = datetime_str()  # 测试开始时生成一次时间戳，保证同一次测试多组文件时间戳一致

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
        update_status(
            "INFO", f"circle fit online start, time: {run_time_tag}")
        module_id = 1
        ml_mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
        ret = ml_mono.ml_set_binning(binn)
        if not ret.success:
            raise RuntimeError(f"ml_set_binning error, msg: {ret.message}")

        # pixel_format = mlcm.MLPixelFormat.MLMono12
        ret = ml_mono.ml_set_pixel_format(pixel_format)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_pixel_format error, msg: {ret.message}")
        for nd in nd_list:
            ret = ml_mono.ml_move_nd_syn(nd)
            if not ret.success:
                raise RuntimeError(f"ml_move_nd_syn error, msg: {ret.message}")

            for xyz in xyz_list:
                ret = ml_mono.ml_move_xyz_syn(xyz)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_move_xyz_syn error, msg: {ret.message}")

                for cyl in cyl_list:
                    for axis in axis_list:
                        rx = mlcm.pyRXCombination(sph=0, cyl=cyl, axis=axis)
                        ret = ml_mono.ml_set_rx_syn(rx)
                        if not ret.success:
                            raise RuntimeError(
                                f"ml_set_rx_syn error, msg: {ret.message}")

                        ret = ml_mono.ml_capture_image_syn()
                        if not ret.success:
                            raise RuntimeError(
                                f"ml_capture_image_syn error, msg: {ret.message}")
                        img = ml_mono.ml_get_image()

                        # excute circle fit
                        # create circle fit instance
                        ml_center_fit = mlcm.pyMLCenterFit(mlcm.MLCenterFit())

                        # load circle fit config
                        status = ml_center_fit.ml_load_circleFit_config(
                            fit_file_path)
                        if not status:
                            raise RuntimeError(
                                "ml_load_circleFit_config error")

                        # excute circle fit, after finish, return the fitted image
                        fitted_img = ml_center_fit.ml_circle_fit(
                            img, rx, xyz, binn)

                        roi_img = fitted_img[roi.y:roi.y +
                                             roi.height, roi.x:roi.x+roi.width]

                        cv2.imwrite(os.path.join(
                            out_path, f"{mlcm.pyRXCombination_to_str(rx)}.tif"), roi_img)
                        update_status(
                            "INFO", f"center fit for: {mlcm.pyRXCombination_to_str(rx)}")
                update_status(
                    "INFO", f"center fit for: {mlcm.MLFilterEnum_to_str(xyz)}")
            update_status(
                "INFO", f"center fit for: {mlcm.MLFilterEnum_to_str(nd)}")
        update_status("INFO", "circle fit finish online")
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg)
        raise
