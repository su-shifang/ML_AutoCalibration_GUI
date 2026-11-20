import mlcolorimeter as mlcm
from typing import List, Dict, Optional, Callable, Literal
import cv2
import os
from datetime import datetime


MsgLevel = Literal["INFO", "WARN", "ERROR"]


def datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]


def capture_image_fixedLUM_afterFFC(
        colorimeter: mlcm.ML_Colorimeter,
        sph_list: List[float],
        cyl_list: List[float],
        axis_list: List[int],
        save_path: str,
        nd_list: List[mlcm.MLFilterEnum],
        xyz_list: List[mlcm.MLFilterEnum],
        ET_list: List[float],
        use_rx: bool,
        binn_selector: mlcm.BinningSelector = mlcm.BinningSelector.Logic,
        binn_mode: mlcm.BinningMode = mlcm.BinningMode.AVERAGE,
        binn: mlcm.Binning = mlcm.Binning.ONE_BY_ONE,
        pixel_format: mlcm.MLPixelFormat = mlcm.MLPixelFormat.MLMono12,
        cali_config: mlcm.pyCalibrationConfig = mlcm.pyCalibrationConfig(),
        status_callback:  Optional[Callable[[MsgLevel, str], None]] = None
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
            "INFO", f"capture image start, time: {run_time_tag}")
        save_path = os.path.join(save_path, run_time_tag)
        os.makedirs(save_path, exist_ok=True)
        module_id = 1
        ml_mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
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

        # set pixel format to MLMono12 for capture
        ret = ml_mono.ml_set_pixel_format(pixel_format)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_pixel_format error, msg: {ret.message}")

        cali_config.light_source_list = [ml_mono.ml_get_light_source()]
        cali_config.aperture = ml_mono.ml_get_aperture()
        cali_config.nd_filter_list = nd_list
        cali_config.color_filter_list = xyz_list
        cali_config.binn = mlcm.Binning.ONE_BY_ONE

        def _capture_and_process_one_group(nd, et, rx):
            capture_data_dict = dict()
            cali_config.rx = rx
            for xyz in xyz_list:
                ret = ml_mono.ml_move_xyz_syn(xyz)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_move_xyz_syn error, msg: {ret.message}")
                exposure = mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=et)
                ret = ml_mono.ml_set_exposure(exposure)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_set_exposure error, msg: {ret.message}")
                ret = ml_mono.ml_capture_image_syn()
                if not ret.success:
                    raise RuntimeError(
                        f"ml_capture_image_syn error, msg: {ret.message}")
                capture_data = ml_mono.ml_get_CaptureData()
                capture_data_dict[xyz] = capture_data
            ret = colorimeter.ml_set_CaptureData(
                module_id, data=capture_data_dict)
            if not ret.success:
                raise RuntimeError(
                    f"ml_set_CaptureData error, msg: {ret.message}")

            # load calibration data by calbration config
            ret = colorimeter.ml_load_calibration_data(cali_config=cali_config)
            if not ret.success:
                raise RuntimeError(
                    f"ml_load_calibration_data error, msg: {ret.message}")

            # execute calibration process for capture data by calibration config
            ret = colorimeter.ml_image_process(cali_config)
            if not ret.success:
                raise RuntimeError(
                    f"ml_image_process error, msg: {ret.message}")
            # get calibration data after calibration process
            processed_data = colorimeter.ml_get_processed_data(module_id)
            nd_str = mlcm.MLFilterEnum_to_str(nd)
            rx_str = mlcm.pyRXCombination_to_str(rx)
            for xyz in xyz_list:
                img_ffc = processed_data[mlcm.CalibrationEnum.FFC][xyz].image
                img_raw = processed_data[mlcm.CalibrationEnum.Raw][xyz].image
                xyz_str = mlcm.MLFilterEnum_to_str(xyz)
                if use_rx:
                    img_name_ffc = f"FFC_{rx_str}_{nd_list}_{xyz_str}_{et}ms.tif"
                    img_name_raw = f"Raw_{rx_str}_{nd_list}_{xyz_str}_{et}ms.tif"
                else:
                    img_name_ffc = f"FFC_{nd_list}_{xyz_str}_{et}ms.tif"
                    img_name_raw = f"Raw_{nd_list}_{xyz_str}_{et}ms.tif"
                img_path_raw = os.path.join(save_path, img_name_raw)
                write_ok = cv2.imwrite(img_path_raw, img_raw)
                if not write_ok:
                    raise IOError(f"save raw fail: {img_path_raw}")
                img_path_ffc = os.path.join(save_path, img_name_ffc)
                write_ok = cv2.imwrite(img_path_ffc, img_ffc)
                if not write_ok:
                    raise IOError(f"save ffc fail: {img_path_raw}")
                update_status(
                    "INFO", f"ET={et}ms, RX={rx_str}, ND={nd_str}, XYZ={xyz_str} raw & ffc saved")

        # ========================开始遍历RX===========================
        if not use_rx:
            rx = mlcm.pyRXCombination(0, 0, 0)
            ret = ml_mono.ml_set_rx_syn(rx)
            if not ret.success:
                raise RuntimeError(f"ml_set_rx_syn error, msg: {ret.message}")
            for nd in nd_list:
                ret = ml_mono.ml_move_nd_syn(nd)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_move_nd_syn error, msg: {ret.message}")
                for et in ET_list:
                    _capture_and_process_one_group(nd, et, rx)
                update_status(
                    "INFO", f"{mlcm.MLFilterEnum_to_str(nd)} capture finish")
        else:
            for nd in nd_list:
                ret = ml_mono.ml_move_nd_syn(nd)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_move_nd_syn error, msg: {ret.message}")
                for et in ET_list:
                    for sph in sph_list:
                        for cyl in cyl_list:
                            for axis in axis_list:
                                rx = mlcm.pyRXCombination(sph, cyl, axis)
                                ret = ml_mono.ml_set_rx_syn(rx)
                                if not ret.success:
                                    raise RuntimeError(
                                        f"ml_set_rx_syn error, msg: {ret.message}")
                                _capture_and_process_one_group(nd, et, rx)
                update_status(
                    "INFO", f"{mlcm.MLFilterEnum_to_str(nd)} capture finish")

        # if not use_rx:
        #     rx = mlcm.pyRXCombination(0, 0, 0)
        #     ret = ml_mono.ml_set_rx_syn(rx)
        #     if not ret.success:
        #         raise RuntimeError(f"ml_set_rx_syn error, msg: {ret.message}")
        #     cali_config.rx = rx
        #     for nd in nd_list:
        #         ret = ml_mono.ml_move_nd_syn(nd)
        #         if not ret.success:
        #             raise RuntimeError(f"ml_move_nd_syn error, msg: {ret.message}")
        #         for et in ET_list:
        #             capture_data_dict = dict()
        #             for xyz in xyz_list:
        #                 ret = ml_mono.ml_move_xyz_syn(xyz)
        #                 if not ret.success:
        #                     raise RuntimeError(f"ml_move_xyz_syn error, msg: {ret.message}")
        #                 exposure = mlcm.pyExposureSetting(
        #                     exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=et)
        #                 ret = ml_mono.ml_set_exposure(exposure)
        #                 if not ret.success:
        #                     raise RuntimeError(f"ml_set_exposure error, msg: {ret.message}")
        #                 ret = ml_mono.ml_capture_image_syn()
        #                 if not ret.success:
        #                     raise RuntimeError(f"ml_capture_image_syn error, msg: {ret.message}")
        #                 capture_data = ml_mono.ml_get_CaptureData()
        #                 capture_data_dict[xyz] = capture_data

        #             ret = colorimeter.ml_set_CaptureData(module_id, data=capture_data_dict)
        #             if not ret.success:
        #                 raise RuntimeError(f"ml_set_CaptureData error, msg: {ret.message}")

        #             # load calibration data by calbration config
        #             ret = colorimeter.ml_load_calibration_data(cali_config=cali_config)
        #             if not ret.success:
        #                 raise RuntimeError(f"ml_load_calibration_data error, msg: {ret.message}")

        #             # execute calibration process for capture data by calibration config
        #             ret = colorimeter.ml_image_process(cali_config)
        #             if not ret.success:
        #                 raise RuntimeError(f"ml_image_process error, msg: {ret.message}")
        #             # get calibration data after calibration process
        #             processed_data = colorimeter.ml_get_processed_data(module_id)
        #             for xyz in xyz_list:
        #                 img_ffc = processed_data[mlcm.CalibrationEnum.FFC][xyz].image
        #                 img_raw = processed_data[mlcm.CalibrationEnum.Raw][xyz].image
        #                 img_name_ffc = f"FFC_{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{et}ms.tiff"
        #                 img_name_raw = f"Raw_{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{et}ms.tiff"
        #                 img_path_raw = os.path.join(save_path, img_name_raw)
        #                 cv2.imwrite(img_path_raw, img_raw)
        #                 img_path_ffc = os.path.join(save_path, img_name_ffc)
        #                 cv2.imwrite(img_path_ffc, img_ffc)
        #             update_status("INFO", f"ET_{str(et)}_{mlcm.pyRXCombination_to_str(rx)} ffc and raw image save success")
        #         update_status("INFO",f"{mlcm.MLFilterEnum_to_str(nd)} capture finish")
        # else:
        #     for nd in nd_list:
        #         ret = ml_mono.ml_move_nd_syn(nd)
        #         if not ret.success:
        #             raise RuntimeError(f"ml_move_nd_syn error, msg: {ret.message}")
        #         for et in ET_list:
        #             for sph in sph_list:
        #                 for cyl in cyl_list:
        #                     for axis in axis_list:
        #                         capture_data_dict = dict()
        #                         rx = mlcm.pyRXCombination(sph, cyl, axis)
        #                         ret = ml_mono.ml_set_rx_syn(rx)
        #                         if not ret.success:
        #                             raise RuntimeError(f"ml_set_rx_syn error, msg: {ret.message}")
        #                         cali_config.rx = rx
        #                         for xyz in xyz_list:
        #                             ret = ml_mono.ml_move_xyz_syn(xyz)
        #                             if not ret.success:
        #                                 raise RuntimeError(f"ml_move_xyz_syn error, msg: {ret.message}")
        #                             exposure = mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=et)
        #                             ret = ml_mono.ml_set_exposure(exposure)
        #                             if not ret.success:
        #                                 raise RuntimeError(f"ml_set_exposure error, msg: {ret.message}")
        #                             ret = ml_mono.ml_capture_image_syn()
        #                             if not ret.success:
        #                                 raise RuntimeError(f"ml_capture_image_syn error, msg: {ret.message}")
        #                             capture_data = ml_mono.ml_get_CaptureData()
        #                             capture_data_dict[xyz] = capture_data

        #                         ret = colorimeter.ml_set_CaptureData(module_id, data=capture_data_dict)
        #                         if not ret.success:
        #                             raise RuntimeError(f"ml_set_CaptureData error, msg: {ret.message}")

        #                         # load calibration data by calbration config
        #                         ret = colorimeter.ml_load_calibration_data(cali_config=cali_config)
        #                         if not ret.success:
        #                             raise RuntimeError(f"ml_load_calibration_data error, msg: {ret.message}")

        #                         # execute calibration process for capture data by calibration config
        #                         ret = colorimeter.ml_image_process(cali_config)
        #                         if not ret.success:
        #                             raise RuntimeError(f"ml_image_process error, msg: {ret.message}")
        #                         # get calibration data after calibration process
        #                         processed_data = colorimeter.ml_get_processed_data(module_id)
        #                         for xyz in xyz_list:
        #                             img_ffc = processed_data[mlcm.CalibrationEnum.FFC][xyz].image
        #                             img_raw = processed_data[mlcm.CalibrationEnum.Raw][xyz].image
        #                             img_name_ffc = f"FFC_{str(sph)}d_{str(cyl)}d_{str(axis)}deg_{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{et}ms.tiff"
        #                             img_name_raw = f"Raw_{str(sph)}d_{str(cyl)}d_{str(axis)}deg_{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{et}ms.tiff"
        #                             img_path_raw = os.path.join(save_path, img_name_raw)
        #                             cv2.imwrite(img_path_raw, img_raw)
        #                             img_path_ffc = os.path.join(save_path, img_name_ffc)
        #                             cv2.imwrite(img_path_ffc, img_ffc)
        #                         update_status("INFO", f"ET_{str(et)}_{mlcm.pyRXCombination_to_str(rx)} ffc and raw image save success")
        #         update_status("INFO", f"{mlcm.MLFilterEnum_to_str(nd)} capture finish")
        update_status("INFO", "finish!")
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg)
        raise


if __name__ == "__main__":
    # set mono module calibration configuration path
    eye1_path = r"F:\SDK\EYE1"

    # 固定亮度，曝光时间列表(亮度通过积分球软件自己设定)
    ET_list = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    # 图片保存路径
    out_path = r"D:\Output\capture_image_fixedLUM"
    os.makedirs(out_path, exist_ok=True)
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

        # nd filter list to switch during capture
        nd_list = [mlcm.MLFilterEnum.ND0]
        # xyz filter list to switch during capture
        xyz_list = [mlcm.MLFilterEnum.Clear]
        use_rx = False
        sph_list = [0]
        cyl_list = [0]
        axis_list = [0]

        cali_config = mlcm.pyCalibrationConfig(
            input_path=eye1_path,
            dark_flag=True,
            ffc_flag=True,
            color_shift_flag=True,
            distortion_flag=True,
            luminance_flag=True
        )

        capture_image_fixedLUM_afterFFC(
            colorimeter=ml_colorimeter,
            sph_list=sph_list,
            cyl_list=cyl_list,
            axis_list=axis_list,
            save_path=out_path,
            nd_list=nd_list,
            xyz_list=xyz_list,
            ET_list=ET_list,
            use_rx=use_rx,
            cali_config=cali_config
        )

    except Exception as e:
        print(f"[ERROR] {e}")
