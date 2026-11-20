import mlcolorimeter as mlcm
from typing import List, Dict, Literal, Optional, Callable
import cv2
import os
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from openpyxl import Workbook

MsgLevel = Literal["INFO", "WARN", "ERROR"]

__all__ = ["cal_synthetic_mean_images", "capture_ffc_images", "cal_uniformity"]


def datetime_str():
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3]


def datetime_str2():
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


def update_status(level: MsgLevel, message: str, callback: Optional[Callable[[MsgLevel, str], None]] = None):
    '''全局统一状态日志打印/回调'''
    msg = f"[{level}] {message}"
    if callback is not None:
        try:
            callback(level, msg)
        except Exception:
            # 回调出错不中断采集，降级打印到控制台
            print(msg)
    else:
        print(msg)


# ffc
def build_rx_combinations(sph_list: List[float], cyl_list: List[float], axis_list: List[int]) -> List[mlcm.pyRXCombination]:
    '''扁平化生成所有RX组合，消除三层嵌套循环'''
    rx_list: List[mlcm.pyRXCombination] = []
    seen: set[tuple[float, float, int]] = set()
    for sph in sph_list:
        key = (sph, 0.0, 0)
        if key not in seen:
            seen.add(key)
            rx_list.append(mlcm.pyRXCombination(sph=sph, cyl=0, axis=0))
    for cyl in cyl_list:
        for axis in axis_list:
            key = (0.0, round(cyl, 2), axis)
            if key not in seen:
                seen.add(key)
                rx_list.append(mlcm.pyRXCombination(sph=0, cyl=cyl, axis=axis))
    return rx_list

# uniformity


def build_uniformity_rx_combinations(
    sph_list: List[float],
    cyl_list: List[float],
    axis_list: List[int]
) -> List[mlcm.pyRXCombination]:
    """均匀性测量：生成全部球镜、柱镜、轴位组合（含球柱联合）"""
    rx_list: List[mlcm.pyRXCombination] = []
    seen = set()
    for sph in sph_list:
        for cyl in cyl_list:
            for axis in axis_list:
                key = (round(sph, 2), round(cyl, 2), axis)
                if key not in seen:
                    seen.add(key)
                    rx_list.append(mlcm.pyRXCombination(
                        sph=sph, cyl=cyl, axis=axis))
    return rx_list


def check_roi_valid(img: np.ndarray, rect: mlcm.pyCVRect) -> bool:
    '''校验ROI是否在图像范围内'''
    h, w = img.shape[:2]
    if rect.x < 0 or rect.y < 0:
        return False
    if rect.x+rect.width > w or rect.y+rect.height > h:
        return False
    return True


def measurement(
    colorimeter: mlcm.ML_Colorimeter,
    half_size: int,
    vrange: List[float],
    nd: mlcm.MLFilterEnum,
    xyz_list: List[mlcm.MLFilterEnum],
    RX_str: str,
    binn: mlcm.Binning,
    exposure_map: Dict[mlcm.MLFilterEnum, mlcm.pyExposureSetting],
    module_id: int,
    cali_config: mlcm.pyCalibrationConfig,
    save_config: mlcm.pySaveDataConfig,
    roi_dict: Dict[mlcm.Binning, List[mlcm.pyCVRect]],
    ffc_ws,
    fourcolor_ws,
    ffc_wb,
    fourcolor_wb,
    ffc_xlsx: str,
    fourcolor_xlsx: str,
    uniformity_path: str,
    status_callback:  Optional[Callable[[MsgLevel, str], None]] = None
):
    try:
        mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
        # capture data
        capture_data_dict = dict()
        for xyz in xyz_list:
            ret = mono.ml_move_xyz_syn(xyz)
            if not ret.success:
                raise RuntimeError(
                    f"ml_move_xyz_syn error, msg: {ret.message}")

            ret = mono.ml_set_exposure(exposure_map[xyz])
            if not ret.success:
                raise RuntimeError(
                    f"ml_set_exposure error, msg: {ret.message}")

            ret = mono.ml_capture_image_syn()
            if not ret.success:
                raise RuntimeError(
                    f"ml_capture_image_syn error, msg: {ret.message}")

            capture_data = mono.ml_get_CaptureData()
            capture_data_dict[xyz] = capture_data
        # set capture data for measurement
        ret = colorimeter.ml_set_CaptureData(module_id, capture_data_dict)
        if not ret.success:
            raise RuntimeError(f"ml_set_CaptureData error, msg: {ret.message}")

        # load calibration data by calbration config
        ret = colorimeter.ml_load_calibration_data(cali_config)
        if not ret.success:
            raise RuntimeError(
                f"ml_load_calibration_data error, msg: {ret.message}")

        # execute calibration process for capture data by calibration config
        ret = colorimeter.ml_image_process(cali_config)
        if not ret.success:
            raise RuntimeError(f"ml_image_process error, msg: {ret.message}")

        # get calibration data after calibration process
        processed_data = colorimeter.ml_get_processed_data(module_id)

        # save calibration data
        ret = colorimeter.ml_save_processed_data(
            module_id, processed_data, save_config)
        if not ret.success:
            raise RuntimeError(
                f"ml_save_processed_data error, msg: {ret.message}")

        roi_list = roi_dict[binn]
        binn_scale = mlcm.Binning_to_Int(binn)
        half_size_scaled = half_size/binn_scale

        for xyz in xyz_list:
            img = processed_data[mlcm.CalibrationEnum.FFC][xyz].image
            xyz_str = mlcm.MLFilterEnum_to_str(xyz)
            nd_str = mlcm.MLFilterEnum_to_str(nd)
            light_src = mono.ml_get_light_source()

            gray_list = []
            for rect in roi_list:
                if not check_roi_valid(img, rect):
                    update_status(
                        "WARN", f"ROI out of image range! RX={RX_str}, XYZ={xyz_str}", status_callback)
                roi_img = img[rect.y: rect.y+rect.height,
                              rect.x: rect.x+rect.width]
                gray = cv2.mean(roi_img)[0]
                gray_list.append(gray)

            mean_val = np.mean(gray_list)
            std_val = np.std(gray_list, ddof=1)
            min_val = min(gray_list)
            max_val = max(gray_list)
            minmax_ratio = min_val/max_val if max_val != 0 else 0.0
            uniformity = 1-0.5*(max_val-min_val) / \
                mean_val if mean_val != 0 else 0.0
            # 写入FFC表格
            row_data = [RX_str, xyz_str, nd_str, light_src] + gray_list + \
                [mean_val, std_val, min_val, max_val, minmax_ratio, uniformity]
            ffc_ws.append(row_data)

            # matplotlib 绘图保存
            row, col = img.shape[0], img.shape[1]
            center_row, center_col = int(row / 2), int(col / 2)

            fig = plt.figure(figsize=(16, 4))
            plt.subplot(1, 2, 1)
            plt.imshow(img, cmap="jet", vmin=vrange[0], vmax=vrange[1])
            plt.xlabel("Col(pixel)")
            plt.ylabel("Row(pixel)")
            plt.colorbar(label="(FFC)")
            plt.title(f"FFC_{mlcm.Binning_to_str(binn)}_{RX_str}_{xyz_str}")
            plt.subplot(1, 2, 2)
            h_line = img[center_row, int(
                center_col - half_size_scaled): int(center_col + half_size_scaled)]
            v_line = img[int(center_row - half_size_scaled): int(center_row + half_size_scaled), center_col]
            plt.plot(h_line)
            plt.plot(v_line)
            plt.grid(which="both")
            plt.xlabel("Position(pixel)")
            plt.ylabel("gray value")
            plt.ylim(vrange)
            plt.legend(["Along-Col", "Along-Row"])
            # 显示图形
            # plt.show(block=True)
            # 保存图形
            img_save_path = os.path.join(
                uniformity_path, f"FFC_{mlcm.Binning_to_str(binn)}_{RX_str}_{xyz_str}.png")
            plt.savefig(img_save_path, bbox_inches="tight")
            plt.close(fig)

        ffc_wb.save(ffc_xlsx)

        # 四色数据统计
        fourcolor_img_list = [
            processed_data[mlcm.CalibrationEnum.FinalResult][mlcm.MLFilterEnum.Y].image,
            processed_data[mlcm.CalibrationEnum.Chroma][mlcm.MLFilterEnum.X].image,
            processed_data[mlcm.CalibrationEnum.Chroma][mlcm.MLFilterEnum.Y].image,
        ]
        fourcolor_img_name_list = ["Luminance", "Cx", "Cy"]

        for idx, img in enumerate(fourcolor_img_list):
            name = fourcolor_img_name_list[idx]
            gray_list = []
            for rect in roi_list:
                if not check_roi_valid(img, rect):
                    update_status(
                        "WARN", f"ROI out of image range!", status_callback)
                roi_img = img[rect.y: rect.y +
                              rect.height, rect.x: rect.x+rect.width]
                gray = cv2.mean(roi_img)[0]
                gray_list.append(gray)

            mean_val = np.mean(gray_list)
            std_val = np.std(gray_list, ddof=1)
            min_val = min(gray_list)
            max_val = max(gray_list)
            minmax_ratio = min_val/max_val if max_val != 0 else 0.0
            uniformity = 1-0.5*(max_val-min_val) / \
                mean_val if mean_val != 0 else 0.0
            row_data = [RX_str, name, nd_str, light_src] + gray_list + \
                [mean_val, std_val, min_val, max_val, minmax_ratio, uniformity]
            fourcolor_ws.append(row_data)

        fourcolor_wb.save(fourcolor_xlsx)
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg, status_callback)
        raise


def cal_synthetic_mean_images(
    colorimeter: mlcm.ML_Colorimeter,
    nd_list: List[mlcm.MLFilterEnum],
    xyz_list: List[mlcm.MLFilterEnum],
    save_path: str,
    status_callback:  Optional[Callable[[MsgLevel, str], None]] = None
):
    update_status("INFO", "cal_synthetic_mean_images start...",
                  status_callback)
    try:
        module_id = 1
        mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
        for nd in nd_list:
            for xyz in xyz_list:
                colorimeter.ml_cal_synthetic_mean_images(
                    module_id=module_id,
                    save_path=save_path,
                    aperture=mono.ml_get_aperture(),
                    nd=nd,
                    xyz=xyz,
                    sphere_list=[0],
                    light_source=mono.ml_get_light_source()
                )
                update_status(
                    "INFO", f"calculate mean images for: {mlcm.MLFilterEnum_to_str(xyz)}", status_callback)
            update_status(
                "INFO", f"calculate mean images for ND: {mlcm.MLFilterEnum_to_str(nd)}", status_callback)
        update_status(
            "INFO", "calculate ffc synthetic mean finish", status_callback)
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg, status_callback)
        raise


def capture_ffc_images(
    colorimeter: mlcm.ML_Colorimeter,
    nd_list: List[mlcm.MLFilterEnum],
    xyz_list: List[mlcm.MLFilterEnum],
    binn: mlcm.Binning,
    exposure_map: Dict[mlcm.MLFilterEnum, Dict[mlcm.MLFilterEnum, mlcm.pyExposureSetting]],
    capture_times: int,
    save_path: str,
    use_RX: bool = False,
    sph_list: Optional[List[float]] = None,
    cyl_list: Optional[List[float]] = None,
    axis_list: Optional[List[int]] = None,
    status_callback:  Optional[Callable[[MsgLevel, str], None]] = None
):
    update_status("INFO", "capture_ffc_images start...", status_callback)
    try:
        module_id = 1
        ml_mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)

        sph_list = sph_list or []
        cyl_list = cyl_list or []
        axis_list = axis_list or []

        # 生成RX组合
        rx_list: List[mlcm.pyRXCombination] = []
        if use_RX and sph_list and cyl_list and axis_list:
            rx_list = build_rx_combinations(sph_list, cyl_list, axis_list)
        else:
            rx_list = [mlcm.pyRXCombination(0, 0, 0)]

        for nd in nd_list:
            ret = ml_mono.ml_move_nd_syn(nd)
            if not ret.success:
                raise RuntimeError(f"ml_move_nd_syn error, msg: {ret.message}")

            ret = ml_mono.ml_set_binning(binn)
            if not ret.success:
                raise RuntimeError(f"ml_set_binning error, msg: {ret.message}")

            for rx in rx_list:
                rx_str = mlcm.pyRXCombination_to_str(rx)
                # capture ffc images
                ret = colorimeter.ml_capture_ffc2(
                    module_id=module_id,
                    save_path=save_path,
                    nd=nd,
                    xyz_list=xyz_list,
                    rx=rx,
                    avg_count=capture_times,
                    exposure_map=exposure_map[nd]
                )
                if not ret.success:
                    raise RuntimeError(
                        f"ml_capture_ffc_colorcamera error, msg: {ret.message}")
                update_status(
                    "INFO", f"capture image for {rx_str}", status_callback)
        update_status("INFO", "capture ffc images finish")
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg, status_callback)
        raise


def cal_uniformity(
    colorimeter: mlcm.ML_Colorimeter,
    half_size: int,
    vrange: List[float],
    nd_list: List[mlcm.MLFilterEnum],
    xyz_list: List[mlcm.MLFilterEnum],
    uniformity_path: str,
    binn_list: List[mlcm.Binning],
    exposure_map: Dict[mlcm.MLFilterEnum, mlcm.pyExposureSetting],
    roi_dict: Dict[mlcm.Binning, List[mlcm.pyCVRect]],
    use_RX: bool = False,
    rx_dict: Optional[Dict[mlcm.MLFilterEnum, List]] = None,
    status_callback:  Optional[Callable[[MsgLevel, str], None]] = None
):
    update_status("INFO", "cal_uniformity start...", status_callback)
    try:
        module_id = 1
        mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)

        cali_path = mono.ml_get_config_path()

        for nd in nd_list:
            file_prefix = f"{datetime_str2()}_{mlcm.MLFilterEnum_to_str(nd)}_{mono.ml_get_aperture()}"
            ffc_xlsx = os.path.join(
                uniformity_path, f"ffc_uniformity-{file_prefix}.xlsx")
            fourcolor_xlsx = os.path.join(
                uniformity_path, f"fourcolor_uniformity-{file_prefix}.xlsx")

            ret = mono.ml_move_nd_syn(nd)
            if not ret.success:
                raise RuntimeError(f"ml_move_nd_syn error, msg: {ret.message}")

            # 获取当前ND对于的RX参数
            sph_list, cyl_list, axis_list = [], [], []
            if use_RX and nd in rx_dict:
                sph_list, cyl_list, axis_list = rx_dict[nd]

            for binn in binn_list:
                ret = mono.ml_set_binning(binn)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_set_binning error, msg: {ret.message}")
                get_binn = mono.ml_get_binning()
                update_status(
                    "INFO", f"Current binning: {get_binn.name}", status_callback)

                # 创建Excel
                ffc_wb = Workbook()
                ffc_wb.remove(ffc_wb.active)
                binn_title = str(pow(2, int(binn))) + "X" + \
                    str(pow(2, int(binn)))
                ffc_ws = ffc_wb.create_sheet(title=binn_title)
                ffc_title = ["RX", "ColorFilter", "NDFilter", "Light Source", "ROI1", "ROI2", "ROI3",
                             "ROI4", "ROI5", "ROI6", "ROI7", "ROI8", "ROI9", "Mean", "Std", "Min", "Max", "Min/Max", "Uniformity"]
                ffc_ws.append(ffc_title)

                fourcolor_wb = Workbook()
                fourcolor_wb.remove(fourcolor_wb.active)
                fourcolor_ws = fourcolor_wb.create_sheet(title=binn_title)
                fourcolor_title = ["RX", "CxCyLuminance", "NDFilter", "Light Source", "ROI1", "ROI2", "ROI3",
                                   "ROI4", "ROI5", "ROI6", "ROI7", "ROI8", "ROI9", "Mean", "Std", "Min", "Max", "Min/Max", "Uniformity"]
                fourcolor_ws.append(fourcolor_title)
                rx_list: List[mlcm.pyRXCombination]
                if not use_RX:
                    rx_list = [mlcm.pyRXCombination(0, 0, 0)]
                else:
                    rx_list = build_uniformity_rx_combinations(
                        sph_list, cyl_list, axis_list)

                for rx in rx_list:
                    ret = mono.ml_set_rx_syn(rx)
                    if not ret.success:
                        raise RuntimeError(
                            f"ml_set_rx_syn error, msg: {ret.message}")
                    RX_str = mlcm.pyRXCombination_to_str(rx)
                    update_status(
                        "INFO", f"Start measurement for rx: {RX_str}", status_callback)
                    # calibration config for measurement
                    cali_config = mlcm.pyCalibrationConfig(
                        input_path=cali_path,
                        aperture=mono.ml_get_aperture(),
                        nd_filter_list=[nd],
                        color_filter_list=xyz_list,
                        rx=rx,
                        light_source_list=[mono.ml_get_light_source()],
                        dark_flag=True,
                        ffc_flag=True,
                        color_shift_flag=True,
                        distortion_flag=True,
                        exposure_flag=True,
                        four_color_flag=True,
                    )

                    # save config
                    save_config = mlcm.pySaveDataConfig(
                        save_path=os.path.join(uniformity_path, "res"),
                        save_raw=True,
                        save_result=True,
                        save_calibration=False,
                        save_chroma=False
                    )

                    measurement(
                        colorimeter=colorimeter,
                        half_size=half_size,
                        vrange=vrange,
                        nd=nd,
                        xyz_list=xyz_list,
                        RX_str=RX_str,
                        binn=binn,
                        exposure_map=exposure_map,
                        module_id=module_id,
                        cali_config=cali_config,
                        save_config=save_config,
                        roi_dict=roi_dict,
                        ffc_ws=ffc_ws,
                        fourcolor_ws=fourcolor_ws,
                        ffc_wb=ffc_wb,
                        fourcolor_wb=fourcolor_wb,
                        ffc_xlsx=ffc_xlsx,
                        fourcolor_xlsx=fourcolor_xlsx,
                        uniformity_path=uniformity_path,
                        status_callback=status_callback
                    )
        update_status("INFO", "cal_uniformity finished", status_callback)

    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg, status_callback)
        raise


if __name__ == '__main__':
    eye1_path = r"D:\MLOptic\MLColorimeter\M25465S2603002C_config_1b_average(at home)\EYE1"
    path_list = [
        eye1_path,
    ]
    uniformity_path = r"E:\testout\aolanduo2_uniformity"
    os.makedirs(uniformity_path, exist_ok=True)
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

        module_id = 1
        ml_mono = ml_colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)

        light_source = "W"
        ml_mono.ml_set_light_source(light_source)

        nd_list = [mlcm.MLFilterEnum.ND0]
        xyz_list = [mlcm.MLFilterEnum.X,
                    mlcm.MLFilterEnum.Y, mlcm.MLFilterEnum.Z]
        # multi frame averaging
        capture_times = 1
        # different exposure map of nd while capture ffc images, colorcamera no XYZ
        exposure_map_obj = {
            mlcm.MLFilterEnum.ND0: {
                mlcm.MLFilterEnum.X: mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=13),
                mlcm.MLFilterEnum.Y: mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=11),
                mlcm.MLFilterEnum.Z: mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=34),
                mlcm.MLFilterEnum.Clear: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=34)
            },
            mlcm.MLFilterEnum.ND1: {
                mlcm.MLFilterEnum.X: mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=120),
                mlcm.MLFilterEnum.Y: mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=90),
                mlcm.MLFilterEnum.Z: mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=280),
                mlcm.MLFilterEnum.Clear: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=34)
            }
        }
        exposure_map = {
            mlcm.MLFilterEnum.X: mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100),
            mlcm.MLFilterEnum.Y: mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100),
            mlcm.MLFilterEnum.Z: mlcm.pyExposureSetting(exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100),
            mlcm.MLFilterEnum.Clear: mlcm.pyExposureSetting(
                exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100)
        }
        # ONE_BY_ONE  TWO_BY_TWO FOUR_BY_FOUR EIGHT_BY_EIGHT  SIXTEEN_BY_SIXTEEN
        # binn of capture ffc images
        binn = mlcm.Binning.ONE_BY_ONE
        # binn list of calculate uniformity
        binn_list = [mlcm.Binning.ONE_BY_ONE]
        # exposure for calculate uniformity
        exposure = mlcm.pyExposureSetting(
            exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100)

        use_RX = False
        # sph, cyl, axis list while capture ffc images
        sph_list = [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6]
        cyl_list = [-4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0]
        axis_list = [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165]
        save_path = eye1_path

        half_size = 3600
        vrange = [15, 390]

        # different rx list of nd while calculate uniformity
        rx_dict = {
            mlcm.MLFilterEnum.ND0: [
                [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4],
                [-4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0],
                [0, 90]
            ],
            mlcm.MLFilterEnum.ND1: [
                [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4],
                [-4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0],
                [0, 90]
            ],
            mlcm.MLFilterEnum.ND2: [
                [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4],
                [-4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0],
                [0, 90]
            ],
            mlcm.MLFilterEnum.ND3: [
                [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4],
                [-4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0],
                [0, 90]
            ],

        }

        # different roi list of binn while calculate uniformity
        roi_dict = {
            mlcm.Binning.ONE_BY_ONE: [
                mlcm.pyCVRect(3000, 2632, 400, 400),
                mlcm.pyCVRect(3000, 4632, 400, 400),
                mlcm.pyCVRect(3000, 6632, 400, 400),
                mlcm.pyCVRect(4900, 2632, 400, 400),
                mlcm.pyCVRect(4900, 4632, 400, 400),
                mlcm.pyCVRect(4900, 6632, 400, 400),
                mlcm.pyCVRect(7800, 2632, 400, 400),
                mlcm.pyCVRect(7800, 4632, 400, 400),
                mlcm.pyCVRect(7800, 6632, 400, 400),
            ],
            mlcm.Binning.TWO_BY_TWO: [
                mlcm.pyCVRect(3000, 2632, 200, 200),
                mlcm.pyCVRect(3000, 4632, 200, 200),
                mlcm.pyCVRect(3000, 6632, 200, 200),
                mlcm.pyCVRect(4900, 2632, 200, 200),
                mlcm.pyCVRect(4900, 4632, 200, 200),
                mlcm.pyCVRect(4900, 6632, 200, 200),
                mlcm.pyCVRect(7800, 2632, 200, 200),
                mlcm.pyCVRect(7800, 4632, 200, 200),
                mlcm.pyCVRect(7800, 6632, 200, 200),
            ],
            mlcm.Binning.FOUR_BY_FOUR: [
                mlcm.pyCVRect(800, 658, 100, 100),
                mlcm.pyCVRect(800, 1158, 100, 100),
                mlcm.pyCVRect(800, 1658, 100, 100),
                mlcm.pyCVRect(1350, 658, 100, 100),
                mlcm.pyCVRect(1350, 1158, 100, 100),
                mlcm.pyCVRect(1350, 1658, 100, 100),
                mlcm.pyCVRect(1900, 658, 100, 100),
                mlcm.pyCVRect(1900, 1158, 100, 100),
                mlcm.pyCVRect(1900, 1658, 100, 100),
            ]
        }

        is_capture_ffc = True
        is_calculate_synthetic = True
        is_calculate_uniformity = True

        if is_capture_ffc:
            capture_ffc_images(
                colorimeter=ml_colorimeter,
                nd_list=nd_list,
                xyz_list=xyz_list,
                binn=binn,
                exposure_map=exposure_map_obj,
                capture_times=capture_times,
                save_path=save_path,
                use_RX=use_RX,
                sph_list=sph_list,
                cyl_list=cyl_list,
                axis_list=axis_list
            )

        if use_RX and is_calculate_synthetic:
            cal_synthetic_mean_images(
                colorimeter=ml_colorimeter,
                nd_list=nd_list,
                xyz_list=xyz_list,
                save_path=save_path
            )

        if is_calculate_uniformity:
            cal_uniformity(
                colorimeter=ml_colorimeter,
                half_size=half_size,
                vrange=vrange,
                nd_list=nd_list,
                xyz_list=xyz_list,
                uniformity_path=uniformity_path,
                binn_list=binn_list,
                exposure_map=exposure_map,
                roi_dict=roi_dict,
                use_RX=use_RX,
                rx_dict=rx_dict
            )

    except Exception as e:
        print(f"[ERROR] {e}")
