import mlcolorimeter as mlcm
import cv2
import os
import json
import logging
import numpy as np
import tkinter as tk
from tkinter import messagebox
import pandas as pd
from datetime import datetime
from typing import List, Dict,Callable,Optional,Literal
import time
import configparser
import re
MsgLevel = Literal["INFO", "WARN", "ERROR"]

# ---------------------- camera configuration ----------------------
BINNING_SELECTOR = mlcm.BinningSelector.Logic
BINNING = mlcm.Binning.ONE_BY_ONE
BINNING_MODE = mlcm.BinningMode.AVERAGE
PIXEL_FORMAT = mlcm.MLPixelFormat.MLMono12
TARGET_GRAY_RATIO = 0.8  # 存入数据取0.8的
SLEEP_INTERVAL = 1.0

# 创建文件夹
def create_directory(path):
    os.makedirs(path, exist_ok=True)


# Function to show a message box with the light source information
def show_message(light_source):
    # Create a hidden root window
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    # Show the message box
    messagebox.showinfo("提示", "请切换光源到: " + light_source)
    root.destroy()


# 保存json数据到文件


def save_json(data, file_path):
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)


def process_image(img, img_x=6688, img_y=4764, roi_width=250, roi_height=250):
    roi_center_x = int(roi_width / 2)
    roi_center_y = int(roi_height / 2)
    roi_list = []
    for x, y in [(img_x, img_y)]:
        y1, y2 = int(y - roi_center_y), int(y + roi_center_y)
        x1, x2 = int(x - roi_center_x), int(x + roi_center_x)
        roi = img[y1: y2, x1: x2]
        grays = cv2.mean(roi)[0]
        roi_list.append(grays)
    return np.mean(roi_list)


def save_results_to_excel(results, out_path):
    results_df = pd.DataFrame(results)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_excel_path = "monocalibration_results" + "_" + timestamp + ".xlsx"
    os.makedirs(out_path, exist_ok=True)
    result_file = os.path.join(out_path, output_excel_path)

    results_df.to_excel(result_file, index=False)
    logging.info(f"Calibration results saved to {result_file}")


def parse_folder_rule(folder_rule: str) -> List[str]:
    """
    解析文件夹命名规则

    Args:
        folder_rule: 命名规则字符串，如 "Aperture_NDFilter_ColorFilter_LightSource"
                    或 "Aperture_LightSource" 或 ""（空字符串）

    Returns:
        规则部分列表，如 ["Aperture", "NDFilter", "ColorFilter", "LightSource"]
    """
    if not folder_rule or not folder_rule.strip():
        return []  # 空规则

    # 按_分割并过滤空字符串
    parts = [part.strip() for part in folder_rule.split("_") if part.strip()]

    # 验证规则部分是否有效
    valid_parts = {"Aperture", "NDFilter", "ColorFilter", "LightSource"}
    for part in parts:
        if part not in valid_parts:
            raise RuntimeError(
                f"警告: 规则中包含无效字段 '{part}'，有效字段为: {', '.join(valid_parts)}")
    return parts


def generate_folder_name(folder_rule: str, aperture: str = "",
                         lightsource: str = "", nd: str = "", xyz: str = "") -> str:

    # 解析规则
    rule_parts = parse_folder_rule(folder_rule)

    # 如果没有规则，返回默认名称或空字符串
    if not rule_parts:
        return ""  # 或者返回空字符串，根据你的需求

    # 定义字段映射和默认值
    field_mapping = {
        "Aperture": aperture,
        "NDFilter": nd,
        "ColorFilter": xyz,  # ColorFilter对应XYZFilter字段
        "LightSource": lightsource
    }

    # 定义字段值的特殊处理函数
    def process_field_value(rule_part: str, value: str) -> str:
        """处理字段值"""
        if not value or str(value).strip() == "":
            return ""

        value = str(value).strip()

        return value

    # 生成文件夹名各部分
    folder_parts = []

    for rule_part in rule_parts:
        if rule_part in field_mapping:
            # 获取对应的字段值
            value = field_mapping[rule_part]
            if value == "":
                continue
            # 处理字段值
            processed_value = process_field_value(rule_part, value)
            folder_parts.append(processed_value)
        else:
            # 如果规则部分不在映射中，直接使用（虽然应该不会发生）
            folder_parts.append(rule_part)

    # 用下划线连接所有部分
    folder_name = "_".join(folder_parts)

    # 清理文件名中的非法字符
    folder_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)

    # 如果最终名称为空，返回默认值
    if not folder_name or folder_name == "_":
        return ""

    return folder_name


def get_lum_rad_folder_rule(config_path: str):
    lum_folder_rule = ''
    rad_folder_rule = ''
    ini_path = os.path.join(config_path, "config.ini")
    if not os.path.exists(ini_path):
        print(f"Configuration file not found: {ini_path}")
        return None, None

    config = configparser.ConfigParser()
    try:
        msg=""
        config.read(ini_path, encoding='utf-8')

        if 'Luminance' in config:
            lum_folder_rule = config['Luminance'].get(
                'Folder_Rule', '').strip()
            lum_suffix = config['Luminance'].get('Suffix', '').strip()
        else:
            msg="config.ini文件中缺少Luminance部分, 请检查eye1路径下的文件"
            return None, None,msg

        if 'Radiance' in config:
            rad_folder_rule = config['Radiance'].get('Folder_Rule', '').strip()
            rad_suffix = config['Radiance'].get('Suffix', '').strip()
        else:
            msg="config.ini文件中缺少Radiance部分, 请检查eye1路径下的文件"
            return None, None,msg
        return lum_folder_rule, rad_folder_rule,msg
    except Exception as e:
        msg = f"读取config.ini文件失败: {str(e)}"
        return None, None,msg



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

def mono_calibration(
        colorimeter: mlcm.ML_Colorimeter,
        nd_list: List[mlcm.MLFilterEnum],
        xyz_list: List[mlcm.MLFilterEnum],
        gray_range: List[float],
        aperture: str,
        light_source: str,
        luminance_values: Dict[mlcm.MLFilterEnum, float],
        luminance_no_xyz: float,
        radiance: float,
        eye1_path: str,
        out_path: str,
        image_point: List[int],
        roi_size: List[int],
        lum_folder_rule: str,
        rad_folder_rule: str,
        binn_selector: mlcm.BinningSelector = mlcm.BinningSelector.Logic,
        binn_mode: mlcm.BinningMode = mlcm.BinningMode.AVERAGE,
        binn: mlcm.Binning = mlcm.Binning.ONE_BY_ONE,
        pixel_format: mlcm.MLPixelFormat = mlcm.MLPixelFormat.MLMono12,
        do_nd: bool = True,
        do_xyz: bool = True,
        expusure_offset: float = 0,
        gray_offset: float = 0,
        exposure_time: float = 100,
        max_time: float = 19000,
        rate: int = 1000000,
        pixel_count: int = 5000,
        use_roi: bool = False,
        save_image: bool = False,
        status_callback: Optional[Callable[[MsgLevel, str], None]] = None
):
    try:
        update_status("INFO", "mono_calibration start", status_callback)
                    
        if len(image_point) < 2 or len(roi_size) < 2:
            raise ValueError(
                "image_point and roi_size must cotain at least 2 elements")
        image_x = int(image_point[0])
        image_y = int(image_point[1])
        roi_width = int(roi_size[0])
        roi_height = int(roi_size[1])
        module_id = 1
        mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
        # set light source
        ret = mono.ml_set_light_source(light_source)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_light_source error, msg: {ret.message}")

        ret = mono.ml_set_binning_selector(binn_selector)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_binning_selector error, msg: {ret.message}")

        # Set binning mode for camera.
        ret = mono.ml_set_binning_mode(binn_mode)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_binning_mode error, msg: {ret.message}")

        ret = mono.ml_set_binning(binn)
        if not ret.success:
            raise RuntimeError(f"ml_set_binning error, msg: {ret.message}")

        # Format of the pixel to use for acquisition.
        ret = mono.ml_set_pixel_format(pixel_format)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_pixel_format error, msg: {ret.message}")

        exposure = mlcm.pyExposureSetting(
            exposure_mode=mlcm.ExposureMode.Auto, exposure_time=exposure_time
        )
        results = []

        # 构建ND循环列表，同一逻辑： 无ND时，用一个空占位
        nd_loop = nd_list if do_nd else [None]
        for nd in nd_loop:
            nd_str = "None"
            if nd is not None:
                nd_str = mlcm.MLFilterEnum_to_str(nd)
                ret = mono.ml_move_nd_syn(nd)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_move_nd_syn error, msg: {ret.message}")
            for gray in gray_range:
                aeparams = mlcm.pyAEParams(dynamic_range=gray, target_max=gray + 0.05, target_min=gray - 0.05,
                                           max_time=max_time, rate=rate, pixel_count=pixel_count, use_roi=use_roi)
                ret = mono.ml_update_AE_params(aeparams)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_update_AE_params error at gray={gray}, msg: {ret.message}")
                # XYZ循环, 无XYZ时，用一个空占位
                xyz_loop = xyz_list if do_xyz else [None]
                for xyz in xyz_loop:
                    xyz_str = "None"
                    if xyz is not None:
                        xyz_str = mlcm.MLFilterEnum_to_str(xyz)
                        ret = mono.ml_move_xyz_syn(xyz)
                        if not ret.success:
                            raise RuntimeError(
                                f"ml_move_xyz_syn error, msg: {ret.message}")
                    ret = mono.ml_set_exposure(exposure=exposure)
                    if not ret.success:
                        raise RuntimeError(
                            f"ml_set_exposure error, msg: {ret.message}")
                    ret = mono.ml_capture_image_syn()
                    if not ret.success:
                        raise RuntimeError(
                            f"ml_capture_image_syn error, msg: {ret.message}")
                    img = mono.ml_get_image()
                    if save_image:
                        cv2.imwrite(os.path.join(
                            out_path, f"{gray}_{nd_str}_{xyz_str}.tif"), img)
                    average_gray = process_image(
                        img, image_x, image_y, roi_width, roi_height)
                    average_gray += gray_offset
                    current_et = mono.ml_get_exposure_time() + expusure_offset
                    # 过程输出
                    update_status(
                        "INFO", f"{nd_str}_{gray}_{xyz_str}_averageGray: {average_gray:.2f}, exposureTime: {current_et:.2f}", status_callback)
                    gray_ET = average_gray/current_et if current_et > 0 else 0
                    # 亮度取值
                    if xyz is not None:
                        lum_val = luminance_values[xyz]
                    else:
                        lum_val = luminance_no_xyz
                    luminance_k = lum_val / gray_ET if gray_ET > 0 else 0
                    radiance_k = radiance / gray_ET if gray_ET > 0 else 0
                    # 存入结果
                    row = {
                        "GrayRaw": gray,
                        "Gray Range": f"{gray * 100:.1f}%",
                        "NDFilter": nd_str,
                        "XYZFilter": xyz_str,
                        "AVEGray": average_gray,
                        "ExposureTime": current_et,
                        "G/ET": gray_ET,
                        "Luminance": lum_val,
                        "K(L)": luminance_k,
                        "Radiance": radiance,
                        "K(R)": radiance_k
                    }
                    results.append(row)
        time.sleep(SLEEP_INTERVAL)

        update_status("INFO", "写入配置中...")
        target_items = [item for item in results if np.isclose(
            item["GrayRaw"], TARGET_GRAY_RATIO)]
        if len(target_items) == 0:
            update_status(
                "WARN", "未测试或未找到80%灰度对应数据，跳过写入Luminance/Radiance JSON", status_callback)
        else:
            update_status(
                "INFO", f"找到 {len(target_items)} 条80%灰度匹配记录，开始生成配置文件夹", status_callback)
            luminance_config_path = os.path.join(eye1_path, "Luminance")
            create_directory(luminance_config_path)
            radiance_config_path = os.path.join(eye1_path, "Radiance")
            create_directory(radiance_config_path)
            for item in target_items:
                nd_filter = item["NDFilter"]
                xyz_filter = item["XYZFilter"]
                lum_file_name = generate_folder_name(
                    lum_folder_rule, aperture, light_source, nd_filter, xyz_filter)
                rad_file_name = generate_folder_name(
                    rad_folder_rule, aperture, light_source, nd_filter, xyz_filter)
                luminance_k = item["K(L)"]
                radiance_k = item["K(R)"]
                luminance_file_path = luminance_config_path if lum_file_name == "" else os.path.join(
                    luminance_config_path, lum_file_name)
                os.makedirs(luminance_file_path, exist_ok=True)
                # 完整的文件路径
                luminance_json_file_path = os.path.join(
                    luminance_file_path, "Luminance.json")
                # 创建要写入的字典
                data = {
                    "Luminance": [[float(luminance_k), 0]]
                }
                save_json(data, luminance_json_file_path)

                radiance_file_path = radiance_config_path if rad_file_name == "" else os.path.join(
                    radiance_config_path, rad_file_name)
                os.makedirs(radiance_file_path, exist_ok=True)
                # 完整的文件路径
                radiance_json_file_path = os.path.join(
                    radiance_file_path, "Radiance.json")
                # 创建要写入的字典
                data1 = {
                    "Radiance": [[float(radiance_k), 0]]
                }
                save_json(data1, radiance_json_file_path)
                update_status(
                    "INFO", f"处理记录: ND={nd_filter}, XYZ={xyz_filter}, K(L)={luminance_k:.4f}", status_callback)
        time.sleep(SLEEP_INTERVAL)
        update_status("INFO", f"写入完成，保存数据表到: {out_path}", status_callback)
        save_results_to_excel(results, out_path)
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg, status_callback)
        raise


def mono_calibration_do_ffc(
        colorimeter: mlcm.ML_Colorimeter,
        binn_selector: mlcm.BinningSelector,
        binn_mode: mlcm.BinningMode,
        binn: mlcm.Binning,
        pixel_format: mlcm.MLPixelFormat,
        nd_list: List[mlcm.MLFilterEnum],
        xyz_list: List[mlcm.MLFilterEnum],
        gray_range: List[float],
        aperture: str,
        light_source: str,
        luminance_values: Dict[mlcm.MLFilterEnum, float],
        luminance_no_xyz: float,
        radiance: float,
        eye1_path: str,
        out_path: str,
        image_point: List[int],
        roi_size: List[int],
        lum_folder_rule: str,
        rad_folder_rule: str,
        do_nd: bool = True,
        do_xyz: bool = True,
        sph_list: List[float] = [0.0],
        cyl_list: List[float] = [0.0],
        axis_list: List[int] = [0],
        expusure_offset: float = 0,
        gray_offset: float = 0,
        exposure_time:float=100,
        max_time:float=19000,
        rate:int=1000000,
        pixel_count:int=5000,
        use_roi:bool=False,
        status_callback: Optional[Callable[[MsgLevel, str], None]] = None
):
    try:
        update_status("INFO", "mono_calibration_do_ffc start", status_callback)
        if len(image_point) < 2 or len(roi_size) < 2:
            raise ValueError("image_point and roi_size must contain at least 2 elements")
        image_x = int(image_point[0])
        image_y = int(image_point[1])
        roi_width = int(roi_size[0])
        roi_height = int(roi_size[1])
        module_id = 1
        mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
        # set light source
        ret = mono.ml_set_light_source(light_source)
        if not ret.success:
            raise RuntimeError(f"ml_set_light_source error, msg: {ret.message}")
        # 统一设置相机参数，和mono_calibration对齐
        cfg_set = [
            ("binning_selector", binn_selector),
            ("binning_mode", binn_mode),
            ("binning", binn),
            ("pixel_format", pixel_format),
        ]
        for cfg_name, cfg_val in cfg_set:
            ret = getattr(mono, f'ml_set_{cfg_name}')(cfg_val)
            if not ret.success:
                raise RuntimeError(f"ml_set_{cfg_name} error, msg: {ret.message}")

        ret = mono.ml_set_aperture(aperture)
        if not ret.success:
            raise RuntimeError(f"ml_set_aperture error, msg: {ret.message}")
        exposure = mlcm.pyExposureSetting(
            exposure_mode=mlcm.ExposureMode.Auto, exposure_time=exposure_time
        )
        results = []
        nd_loop = nd_list if do_nd else [None]
        for nd in nd_loop:
            nd_str="None"
            if nd is not None:
                nd_str=mlcm.MLFilterEnum_to_str(nd)
                ret = mono.ml_move_nd_syn(nd)
                if not ret.success:
                    raise RuntimeError(f"ml_move_nd_syn error, msg: {ret.message}")
            for gray in gray_range:
                aeparams = mlcm.pyAEParams(dynamic_range=gray, target_max=gray +
                                        0.05, target_min=gray - 0.05, max_time=max_time, rate=rate, pixel_count=pixel_count,use_roi=use_roi)
                ret = mono.ml_update_AE_params(aeparams)
                if not ret.success:
                    raise RuntimeError(f"ml_update_AE_params error at gray={gray}, msg: {ret.message}")
                for sph in sph_list:
                        for cyl in cyl_list:
                            for axis in axis_list:
                                rx = mlcm.pyRXCombination(
                                    sph=sph, cyl=cyl, axis=axis)
                                ret = mono.ml_set_rx_syn(rx)
                                if not ret.success:
                                    raise RuntimeError(f"ml_set_rx_syn error, msg: {ret.message}")
                                RX_str = mlcm.pyRXCombination_to_str(rx)
                                capture_data_dict: Dict[mlcm.MLFilterEnum, mlcm.pyCaptureData] = dict()
                                cali_config = mlcm.pyCalibrationConfig(
                                    input_path=mono.ml_get_config_path(),
                                    aperture=mono.ml_get_aperture(),
                                    nd_filter_list=[nd] if nd is not None else [mlcm.MLFilterEnum.ND0],
                                    color_filter_list=xyz_list if xyz_list else [mlcm.MLFilterEnum.X],
                                    rx=rx,
                                    light_source_list=[mono.ml_get_light_source()],
                                    dark_flag=True,
                                    ffc_flag=True,
                                    color_shift_flag=False,
                                    distortion_flag=False,
                                    exposure_flag=False,
                                    four_color_flag=False
                                )

                                if do_xyz:
                                    ret=mono.ml_set_exposure(exposure=exposure)
                                    if not ret.success:
                                        raise RuntimeError(f"ml_set_exposure error, msg: {ret.message}")
                                    ret = mono.ml_capture_image_syn()
                                    if not ret.success:
                                        raise RuntimeError(f"ml_capture_image_syn error, msg: {ret.message}")
                                    capture_data = mono.ml_get_CaptureData()
                                    # 这里给一个默认XYZ值
                                    capture_data_dict[mlcm.MLFilterEnum.X] = capture_data
                                    ret = colorimeter.ml_set_CaptureData(module_id, capture_data_dict)
                                    if not ret.success:
                                        raise RuntimeError(f"ml_set_CaptureData error, msg: {ret.message}")
                                    # load calibration data by calbration config
                                    ret = colorimeter.ml_load_calibration_data(cali_config)
                                    if not ret.success:
                                        raise RuntimeError(f"ml_load_calibration_data error, msg: {ret.message}")

                                    # execute calibration process for capture data by calibration config
                                    ret = colorimeter.ml_image_process(cali_config)
                                    if not ret.success:
                                        raise RuntimeError(f"ml_image_process error, msg: {ret.message}")

                                    # get calibration data after calibration process
                                    processed_data = colorimeter.ml_get_processed_data(module_id)

                                    img = processed_data[mlcm.CalibrationEnum.FFC][mlcm.MLFilterEnum.X].image
                                    average_gray = process_image(img, image_x, image_y, roi_width, roi_height)
                                    average_gray += gray_offset
                                    exposure_time = mono.ml_get_exposure_time() + expusure_offset
                                    update_status(
                                        f"{str(gray)}_{RX_str}_averageGray:{str(average_gray)}_exposureTime:{str(exposure_time)}")
                                    gray_ET = average_gray / exposure_time if exposure_time > 0 else 0
                                    luminance_k = luminance_no_xyz / gray_ET if gray_ET > 0 else 0
                                    radiance_k = radiance / gray_ET if gray_ET > 0 else 0
                                    results.append({
                                        "GrayRaw": gray,
                                        "Gray Range": f"{gray * 100:.1f}" + "%",
                                        "NDFilter": nd_str,
                                        "XYZFilter": "None",
                                        "RX": RX_str,
                                        "AVEGray": average_gray,
                                        "ExposureTime": exposure_time,
                                        "G/ET": gray_ET,
                                        "Luminance": luminance_no_xyz,
                                        "K(L)": luminance_k,
                                        "Radiance": radiance,
                                        "K(R)": radiance_k
                                    })
                                else:
                                    for xyz in xyz_list:
                                        ret = mono.ml_move_xyz_syn(xyz)
                                        if not ret.success:
                                            raise RuntimeError(f"ml_move_xyz_syn error, msg: {ret.message}")
                                        ret = mono.ml_set_exposure(exposure=exposure)
                                        if not ret.success:
                                            raise RuntimeError(f"ml_set_exposure error, msg: {ret.message}")
                                        ret = mono.ml_capture_image_syn()
                                        if not ret.success:
                                            raise RuntimeError(f"ml_capture_image_syn error, msg: {ret.message}")
                                        capture_data = mono.ml_get_CaptureData()
                                        capture_data_dict[xyz] = capture_data
                                        ret = colorimeter.ml_set_CaptureData(module_id, capture_data_dict)
                                        if not ret.success:
                                            raise RuntimeError(f"ml_set_CaptureData error, msg: {ret.message}")
                                        ret = colorimeter.ml_load_calibration_data(cali_config)
                                        if not ret.success:
                                            raise RuntimeError(f"ml_load_calibration_data error, msg: {ret.message}")
                                        ret = colorimeter.ml_image_process(cali_config)
                                        if not ret.success:
                                            raise RuntimeError(f"ml_image_process error, msg: {ret.message}")
                                        processed_data = colorimeter.ml_get_processed_data(module_id)
                                        img = processed_data[mlcm.CalibrationEnum.FFC][xyz].image
                                        average_gray = process_image(img, image_x, image_y, roi_width, roi_height)
                                        average_gray += gray_offset
                                        current_et = mono.ml_get_exposure_time() + expusure_offset
                                        gray_ET = average_gray / current_et if current_et > 0 else 0
                                        L_val = luminance_values[xyz]
                                        luminance_k = L_val / gray_ET if gray_ET > 0 else 0
                                        radiance_k = radiance / gray_ET if gray_ET > 0 else 0
                                        xyz_str = mlcm.MLFilterEnum_to_str(xyz)
                                        update_status("INFO", f"{nd_str}_{gray}_{xyz_str}_{RX_str}_averageGray:{average_gray:.2f}, exposureTime:{current_et:.2f}", status_callback)
                                        row = {
                                            "GrayRaw": gray,
                                            "Gray Range": f"{gray * 100:.1f}%",
                                            "NDFilter": nd_str,
                                            "XYZFilter": xyz_str,
                                            "RX": RX_str,
                                            "AVEGray": average_gray,
                                            "ExposureTime": current_et,
                                            "G/ET": gray_ET,
                                            "Luminance": L_val,
                                            "K(L)": luminance_k,
                                            "Radiance": radiance,
                                            "K(R)": radiance_k
                                        }
                                        results.append(row)

        time.sleep(SLEEP_INTERVAL)
        update_status("INFO","写入配置中...",status_callback)

        target_items = [item for item in results if np.isclose(item["GrayRaw"], TARGET_GRAY_RATIO)]
        if len(target_items) == 0:
            update_status("WARN", "未找到80%灰度对应数据，跳过写入Luminance/Radiance JSON", status_callback)
        else:
            update_status("INFO", f"找到 {len(target_items)} 条80%灰度匹配记录，开始生成配置文件夹", status_callback)
            luminance_config_path = os.path.join(eye1_path, "Luminance")
            create_directory(luminance_config_path)
            radiance_config_path = os.path.join(eye1_path, "Radiance")
            create_directory(radiance_config_path)
            for item in target_items:
                nd_filter = item["NDFilter"]
                xyz_filter = item["XYZFilter"]
                lum_file_name = generate_folder_name(lum_folder_rule, aperture, light_source, nd_filter, xyz_filter)
                rad_file_name = generate_folder_name(rad_folder_rule, aperture, light_source, nd_filter, xyz_filter)
                luminance_k = item["K(L)"]
                radiance_k = item["K(R)"]
                luminance_file_path = luminance_config_path if lum_file_name == "" else os.path.join(luminance_config_path, lum_file_name)
                os.makedirs(luminance_file_path, exist_ok=True)
                luminance_json_file_path = os.path.join(luminance_file_path, "Luminance.json")
                data = {"Luminance": [[float(luminance_k), 0]]}
                save_json(data, luminance_json_file_path)

                radiance_file_path = radiance_config_path if rad_file_name == "" else os.path.join(radiance_config_path, rad_file_name)
                os.makedirs(radiance_file_path, exist_ok=True)
                radiance_json_file_path = os.path.join(radiance_file_path, "Radiance.json")
                data1 = {"Radiance": [[float(radiance_k), 0]]}
                save_json(data1, radiance_json_file_path)
                update_status("INFO", f"处理记录: ND={nd_filter}, XYZ={xyz_filter}, RX={item.get('RX','')}, K(L)={luminance_k:.4f}", status_callback)
        time.sleep(SLEEP_INTERVAL)
        update_status("INFO", f"写入完成，保存数据表到: {out_path}", status_callback)
        save_results_to_excel(results, out_path)
        
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg, status_callback)
        raise


if __name__ == "__main__":
    eye1_path = r"D:\MLOptic\MLColorimeter\weilaixing\EYE1"
    aperture = "2.65mm"
    # 选择光源
    light_source = "W"
    # 定义亮度值映射
    luminance_values = {
        mlcm.MLFilterEnum.X: 100,
        mlcm.MLFilterEnum.Y: 150,
        mlcm.MLFilterEnum.Z: 200,
        mlcm.MLFilterEnum.Clear: 1000
    }
    luminance_no_xyz = 1000
    # 设置Radiance
    Radiance = 100
    # 输出路径
    out_path = r"E:\testout\calibrations" + "\\" + light_source

    # switch light source
    show_message(light_source)
    with mlcm.ML_Colorimeter() as ml_colorimeter:
        path_list = [
            eye1_path,
        ]
        # nd filter keyword, from the "Key" field in NDFilterConfig.json
        nd_key = "NDFilter"
        # xyz filter keyword, from the "Key" field in NDFilterConfig.json
        xyz_key = "ColorFilter"

        do_nd = True   # False: module not have NDFilter
        do_xyz = True  # False: module not have XYZFilter
        # nd filter to switch during measurement
        nd_list = [mlcm.MLFilterEnum.ND0, mlcm.MLFilterEnum.ND1, mlcm.MLFilterEnum.ND2, mlcm.MLFilterEnum.ND3, mlcm.MLFilterEnum.ND4]
        # xyz filter to switch during measurement
        xyz_list = [mlcm.MLFilterEnum.X, mlcm.MLFilterEnum.Y, mlcm.MLFilterEnum.Z, mlcm.MLFilterEnum.Clear]
        
        # gray range for calibration
        gray_range = [0.5, 0.6, 0.7, 0.8, 0.9]

        # roi point and size for image processing, to calculate average gray value
        image_point = [5632, 4600]
        roi_size = [300, 300]
        lum_folder_rule, rad_folder_rule = get_lum_rad_folder_rule(eye1_path)

        # 1、连接对应模块
       # add mono module into ml_colorimeter system, according to path_list create one or more mono module
        ret = ml_colorimeter.ml_add_module(path_list=path_list)
        if not ret.success:
            raise RuntimeError("ml_add_module error")
        # connect all module in the ml_colorimeter system
        ret = ml_colorimeter.ml_connect()
        if not ret.success:
            raise RuntimeError("ml_connect error")

        mono_calibration(
            colorimeter=ml_colorimeter,
            nd_list=nd_list,
            xyz_list=xyz_list,
            gray_range=gray_range,
            aperture=aperture,
            light_source=light_source,
            luminance_values=luminance_values,
            luminance_no_xyz=luminance_no_xyz,
            radiance=Radiance,
            eye1_path=eye1_path,
            out_path=out_path,
            image_point=image_point,
            roi_size=roi_size,
            lum_folder_rule=lum_folder_rule,
            rad_folder_rule=rad_folder_rule,
            do_nd=do_nd,
            do_xyz=do_xyz
        )
