import mlcolorimeter as mlcm
from typing import List, Dict, Optional, Callable, Literal
import cv2
from datetime import datetime
import os

MsgLevel = Literal["INFO", "WARN", "ERROR"]


def datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]


def capture_colorfilter_center(
        colorimeter: mlcm.ML_Colorimeter,  # 色度计对象
        save_path: str,  # 图像保存路径
        nd_list: List[mlcm.MLFilterEnum],  # 滤光片ND列表
        xyz_list: List[mlcm.MLFilterEnum],  # 滤光片XYZ列表
        exposure_map_obj: Dict[mlcm.MLFilterEnum,
                               # 曝光设置映射字典
                               Dict[mlcm.MLFilterEnum, mlcm.pyExposureSetting]] = {},
        rx: mlcm.pyRXCombination = mlcm.pyRXCombination(
            sph=0, cyl=0, axis=0),  # RX组合参数
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
            print(msg)  # 如果没有回调函数，直接打印到控制台
    try:
        update_status(
            "INFO", f"capture colorfilter center start, time: {run_time_tag}")

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
                f"ml_set_pixel_format error, msg: {ret.message}")

        ret = ml_mono.ml_set_rx_syn(rx)
        if not ret.success:
            raise RuntimeError(f"ml_set_rx_syn, msg: {ret.message}")

        for nd in nd_list:
            ret = ml_mono.ml_move_nd_syn(nd)
            if not ret.success:
                raise RuntimeError(f"ml_move_nd_syn error, msg: {ret.message}")

            for xyz in xyz_list:
                ret = ml_mono.ml_move_xyz_syn(xyz)
                if not ret.success:
                    raise RuntimeError(f"ml_move_xyz_syn, msg: {ret.message}")

                ret = ml_mono.ml_set_exposure(exposure_map_obj[nd][xyz])
                if not ret.success:
                    raise RuntimeError(
                        f"ml_set_exposure error, msg: {ret.message}")

                ret = ml_mono.ml_capture_image_syn()
                if not ret.success:
                    raise RuntimeError(
                        f"ml_capture_image_syn error, msg: {ret.message}")

                get_image = ml_mono.ml_get_image()
                img_path = os.path.join(
                    save_path, f"{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{run_time_tag}.tif")

                cv2.imwrite(img_path, get_image)
                update_status(
                    "INFO", f"capture image for : {mlcm.MLFilterEnum_to_str(nd)}-{mlcm.MLFilterEnum_to_str(xyz)}")
            update_status(
                "INFO", f"capture image for : {mlcm.MLFilterEnum_to_str(nd)}")
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
        rx = mlcm.pyRXCombination(sph=0, cyl=0, axis=0)

        capture_colorfilter_center(
            colorimeter=ml_colorimeter,
            save_path=save_path,
            nd_list=nd_list,
            xyz_list=xyz_list,
            exposure_map_obj=exposure_map,
            rx=rx
        )
    except Exception as e:
        print(f"[ERROR] {e}")
