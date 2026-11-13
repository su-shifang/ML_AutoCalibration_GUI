import mlcolorimeter as mlcm
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image
from typing import List, Dict, Optional, Callable, Literal
from datetime import datetime
MsgLevel = Literal["INFO", "WARN", "ERROR"]


def preprocess_image(img, block_size):
    height, width = img.shape[:2]
    new_height = height - (height % block_size)
    new_width = width - (width % block_size)
    cropped_img = img[:new_height, :new_width]  # 裁剪多余像素
    return cropped_img


def datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]


def generate_heatmap(image, block_size):
    h, w = image.shape[:2]
    heatmap = np.zeros((h // block_size, w // block_size))
    for i in range(0, h, block_size):
        for j in range(0, w, block_size):
            block = image[i: i + block_size, j: j + block_size]
            heatmap[i // block_size, j //
                    block_size] = np.mean(block)  # 计算块的平均值
    return heatmap


def capture_dark_heatmap(
        colorimeter: mlcm.ML_Colorimeter,
        nd_list: List[mlcm.MLFilterEnum],
        xyz_list: List[mlcm.MLFilterEnum],
        binning_list: List[mlcm.Binning],
        et_list: List[float],
        save_path: str,
        capture_times: int,
        file_name: str = "dark_heatmap",
        binn_selector: mlcm.BinningSelector = mlcm.BinningSelector.Logic,
        binn_mode: mlcm.BinningMode = mlcm.BinningMode.AVERAGE,
        binn: mlcm.Binning = mlcm.Binning.ONE_BY_ONE,
        pixel_format: mlcm.MLPixelFormat = mlcm.MLPixelFormat.MLMono12,
        block_size: int = 10,
        img_fig_width: int = 300,
        img_fig_height: int = 200,
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
        update_status("INFO", f"capture dark heatmap start, run_time_tag: {run_time_tag}")
        os.makedirs(save_path, exist_ok=True)
        raw_path = os.path.join(save_path, "raw")
        os.makedirs(raw_path, exist_ok=True)
        processed_path = os.path.join(save_path, "processed")
        os.makedirs(processed_path, exist_ok=True)
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

        # Format of the pixel to use for acquisition.
        ret = ml_mono.ml_set_pixel_format(pixel_format)
        if not ret.success:
            raise RuntimeError(
                f"ml_set_pixel_format error, msg: {ret.message}")

        def _make_heatmap_png(img: np.ndarray, png_path: str, title: str) -> np.ndarray:
            cropped = preprocess_image(img, block_size)
            heatmap = generate_heatmap(cropped, block_size)
            fig = plt.figure()
            plt.imshow(heatmap, cmap="jet", interpolation="nearest")
            plt.colorbar()
            plt.title(title)
            plt.savefig(png_path)
            plt.close(fig)
            return heatmap

        for nd in nd_list:
            ret = ml_mono.ml_move_nd_syn(nd)
            if not ret.success:
                raise RuntimeError(f"ml_move_nd_syn error, msg: {ret.message}")
            for xyz in xyz_list:
                ret = ml_mono.ml_move_xyz_syn(xyz)
                if not ret.success:
                    raise RuntimeError(
                        f"ml_move_xyz_syn error, msg: {ret.message}")
                file_path = os.path.join(
                    save_path, f"{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{file_name}_{run_time_tag}.xlsx")
                wb = Workbook()
                wb.save(file_path)
                wb = load_workbook(file_path)
                wb.remove(wb["Sheet"])
                for binn in binning_list:
                    ret = ml_mono.ml_set_binning(binn)
                    if not ret.success:
                        raise RuntimeError(
                            f"ml_set_binning error, msg: {ret.message}")
                    binn_int = mlcm.Binning_to_Int(binn)
                    binning_str = f"{(binn_int)}X{(binn_int)}"
                    ws = wb.create_sheet(title=binning_str)
                    gray_list: List[float] = []
                    raw_list: List[np.ndarray] = []
                    raw_max_list: List[float] = []
                    processed_max_list: List[float] = []

                    # ===================================采集平均参考图=======================
                    for et in et_list:
                        update_status(
                            "INFO", f"Binning: {binning_str}, ET: {et}ms, Round1: capture average reference image")
                        exposure = mlcm.pyExposureSetting(
                            exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=et)
                        ret = ml_mono.ml_set_exposure(exposure)
                        if not ret.success:
                            raise RuntimeError(
                                f"ml_set_exposure error, msg: {ret.message}")
                        img_stack = []
                        for i in range(capture_times):
                            ret = ml_mono.ml_capture_image_syn()
                            if not ret.success:
                                raise RuntimeError(
                                    f"ml_capture_image_syn error, msg: {ret.message}")
                            get_img = ml_mono.ml_get_image()
                            img_stack.append(get_img)
                        average_image = np.mean(
                            img_stack, axis=0).astype(np.uint16)
                        gray_list.append(cv2.mean(average_image)[0])
                        raw_list.append(average_image)
                        img_path = os.path.join(
                            raw_path, f"raw_{binning_str}_{str(et)}ms.tif")
                        cv2.imwrite(img_path, average_image)

                    # ===================================采集单帧采集，生成热力图=======================
                    current_row = 19
                    for k in range(len(et_list)):
                        et = et_list[k]
                        update_status(
                            "INFO", f"Binning: {binning_str}, ET: {et}ms, Round2: capture single image for heatmap")
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
                        get_img = ml_mono.ml_get_image()

                        # raw heatmap
                        plt_name = f"raw_{binning_str}_{et}ms"
                        plt_path = os.path.join(raw_path, f"{plt_name}.png")
                        raw_heatmap = _make_heatmap_png(
                            get_img, plt_path, plt_name)
                        raw_max_list.append(np.max(raw_heatmap))
                        img = Image(plt_path)
                        img.width = img_fig_width
                        img.height = img_fig_height
                        ws[f"B{current_row}"] = f"raw {et} ms"
                        ws.add_image(img, f"B{current_row+2}")

                        # processed diff image, clip 防止负数溢出
                        diff_img = np.subtract(
                            np.array(get_img, dtype=np.int16), np.array(raw_list[k], dtype=np.int16))
                        diff_img = np.clip(diff_img, 0, None)
                        plt_name2 = f"processed_{binning_str}_{et}ms"
                        plt_path2 = os.path.join(
                            processed_path, f"{plt_name2}.png")
                        proc_heatmap = _make_heatmap_png(
                            diff_img, plt_path2, plt_name2)
                        processed_max_list.append(np.max(proc_heatmap))
                        img2 = Image(plt_path2)
                        img2.width = img_fig_width
                        img2.height = img_fig_height
                        ws[f"I{current_row}"] = f"processed {et} ms"
                        ws.add_image(img2, f"I{current_row+2}")

                        arr32 = proc_heatmap.astype(np.float32)
                        cv2.imwrite(os.path.join(processed_path,
                                    f"processed_{binning_str}_{et}ms.tif"), arr32)
                        current_row += 15

                    # 写入表格数据
                    ws["B1"] = "No."
                    ws["C1"] = "ET(ms)"
                    ws["D1"] = "Grayscale"
                    ws["E1"] = "10X10 pixel raw max"
                    ws["F1"] = "10X10 pixel processed max"

                    for row in range(len(et_list)):
                        ws[f"B{row+2}"] = row + 1
                        ws[f"C{row+2}"] = et_list[row]
                        ws[f"D{row+2}"] = gray_list[row]
                        ws[f"E{row+2}"] = raw_max_list[row]
                        ws[f"F{row+2}"] = processed_max_list[row]

                    wb.save(file_path)
                    update_status(
                        "INFO", f"{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{mlcm.Binning_to_str(binn)} capture finish")
                update_status(
                    "INFO", f"{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)} capture finish")
            update_status(
                "INFO", f"{mlcm.MLFilterEnum_to_str(nd)} capture finish")
        update_status("INFO", "dark heatmap capture all finished")
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg)
        raise


if __name__ == "__main__":
    # set mono module calibration configuration path
    eye1_path = r"D:\MLOptic\MLColorimeter\M25465S2603002C_config_1b_average(at home)\EYE1"
    save_path = r"E:\testout\dark"
    if not os.path.exists(save_path):
        os.makedirs(save_path)

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
        xyz_list = [mlcm.MLFilterEnum.X]
        binning_list = [mlcm.Binning.ONE_BY_ONE]
        et_list = [1, 2, 5]
        capture_times = 1

        capture_dark_heatmap(
            colorimeter=ml_colorimeter,
            nd_list=nd_list,
            xyz_list=xyz_list,
            binning_list=binning_list,
            et_list=et_list,
            save_path=save_path,
            capture_times=capture_times
        )
    except Exception as e:
        print(f"[ERROR] {e}")
