import mlcolorimeter as mlcm
from typing import List, Dict, Optional, Callable, Literal
import cv2
import os
from datetime import datetime

MsgLevel = Literal["INFO", "WARN", "ERROR"]


def datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]


def capture_RX_center(
        colorimeter: mlcm.ML_Colorimeter,
        sph_list: List[float],
        cyl_list: List[float],
        axis_list: List[int],
        save_path: str,
        nd_list: List[mlcm.MLFilterEnum],
        xyz_list: List[mlcm.MLFilterEnum],
        roi: mlcm.pyCVRect,
        exposure_map_obj: Dict[mlcm.MLFilterEnum,
                               Dict[mlcm.MLFilterEnum, mlcm.pyExposureSetting]] = {},
        status_callback: Optional[Callable[[
            MsgLevel, str], None]] = None  # 状态回调函数
):
    run_time_tag = datetime_str()  # 测试开始时生成一次时间戳，保证同一次测试多组文件时间戳一致

    def update_status(level: MsgLevel, message: str):  # 更新状态的内部函数
        msg = f"[{level}] {message}"  # 格式化状态消息
        if status_callback is not None:  # 如果有回调函数，则调用回调
            try:
                status_callback(level, msg)  # 尝试调用回调函数
            except Exception:
                # 回调出错不中断采集，降级打印到控制台
                print(msg)  # 如果回调失败，打印到控制台
        else:
            print(msg)

    try:
        update_status(
            "INFO", f"capture RX center start, time: {run_time_tag}")
        # 创建保存目录
        os.makedirs(save_path, exist_ok=True)
        # 参数校验
        if exposure_map_obj is None:
            raise ValueError(
                "exposure_map_obj cannot be None, please provide exposure setting dict")
        if not nd_list or not xyz_list:
            raise ValueError("nd_list / xyz_list can not be empty")

        module_id = 1
        ml_mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
        pixel_format = mlcm.MLPixelFormat.MLMono12
        ret = ml_mono.ml_set_pixel_format(pixel_format)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_pixel_format error, ret: {ret.message}")

        for nd in nd_list:
            ret = ml_mono.ml_move_nd_syn(nd)
            if not ret.success:
                raise RuntimeError(f"ml_move_nd_syn error, ret: {ret.message}")

            for xyz in xyz_list:
                ret = ml_mono.ml_move_xyz_syn(xyz)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_move_xyz_syn error,ret: {ret.message}")

                out_path = os.path.join(
                    save_path, f"{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}")
                os.makedirs(out_path, exist_ok=True)

                ret = ml_mono.ml_set_exposure(
                    exposure_map_obj[nd][xyz])
                if not ret.success:
                    raise RuntimeError(
                        f"ml_set_exposure error, ret: {ret.message}")

                for sph in sph_list:
                    for cyl in cyl_list:
                        for axis in axis_list:
                            rx = mlcm.pyRXCombination(
                                sph=sph, cyl=cyl, axis=axis)
                            ret = ml_mono.ml_set_rx_syn(rx)
                            if not ret.success:
                                raise RuntimeError(
                                    f"ml_set_rx_syn error, ret: {ret.message}")

                            ret = ml_mono.ml_capture_image_syn()
                            if not ret.success:
                                raise RuntimeError(
                                    f"ml_capture_image_syn error, ret: {ret.message}")

                            get_image = ml_mono.ml_get_image()
                            img_path = os.path.join(
                                out_path, f"{mlcm.pyRXCombination_to_str(rx)}.tif")
                            roi_img = get_image[roi.y:roi.y +
                                                roi.height, roi.x:roi.x+roi.width]
                            cv2.imwrite(img_path, roi_img)
                            update_status("INFO",
                                          f"{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{mlcm.pyRXCombination_to_str(rx)} capture success")
        update_status("INFO", "capture all images finish")
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg)
        raise


if __name__ == "__main__":
    eye1_path = r"I:\duling ffc\EYE1"
    save_path = r"D:\capture_colorfilter_center"
    path_list = [
        eye1_path,
    ]
    try:
        # create a ML_Colorimeter system instance
        ml_colorimeter = mlcm.ML_Colorimeter()
        # add mono module into ml_colorimeter system, according to path_list create one or more mono module
        ret = ml_colorimeter.ml_add_module(path_list=path_list)
        if not ret.success:
            raise RuntimeError(f"ml_add_module error, msg: {ret.message}")
        # connect all module in the ml_colorimeter system
        ret = ml_colorimeter.ml_connect()
        if not ret.success:
            raise RuntimeError(f"ml_connect error, msg: {ret.message}")

        nd_list = [mlcm.MLFilterEnum.ND0]
        # xyz filter list to switch during capture
        xyz_list = [
            mlcm.MLFilterEnum.X,
            mlcm.MLFilterEnum.Y,
            mlcm.MLFilterEnum.Z,
            mlcm.MLFilterEnum.Clear,
        ]
        sph_list = [0]
        cyl_list = [0]
        axis_list = [0]
        roi = mlcm.pyCVRect(2563, 1542, 200, 200)
        # exposure map of color filter during capture
        exposure_map = {
            mlcm.MLFilterEnum.ND0: {
                mlcm.MLFilterEnum.X: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100
                ),
                mlcm.MLFilterEnum.Y: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100
                ),
                mlcm.MLFilterEnum.Z: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100
                ),
                mlcm.MLFilterEnum.Clear: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100
                ),
            }
        }
        capture_RX_center(
            colorimeter=ml_colorimeter,
            sph_list=sph_list,
            cyl_list=cyl_list,
            axis_list=axis_list,
            save_path=save_path,
            nd_list=nd_list,
            xyz_list=xyz_list,
            roi=roi,
            exposure_map_obj=exposure_map,
        )
    except Exception as e:
        print(f"[ERROR] {e}")
