import mlcolorimeter as mlcm
from typing import List, Dict, Optional, Callable, Literal
import cv2
from datetime import datetime
from openpyxl import Workbook, load_workbook
import os
MsgLevel = Literal["INFO", "WARN", "ERROR"]


def datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]


def calculate_sph_cyl_coefficinet(
        colorimeter: mlcm.ML_Colorimeter,
        save_path: str,
        file_name: str,
        nd: mlcm.MLFilterEnum,
        exposure: mlcm.pyExposureSetting,
        avg_count: int,
        sph_list: List[float],
        cyl_list: List[float],
        roi: mlcm.pyCVRect,
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
            "INFO", f"[colorcamera] calculate sph and cyl coefficient start,time: {run_time_tag}")
        os.makedirs(save_path, exist_ok=True)
        mudule_id = 1
        ml_mono = colorimeter.ml_bino_manage.ml_get_module_by_id(
            module_id=mudule_id)
        pixel_format = mlcm.MLPixelFormat.MLBayerRG12
        ret = ml_mono.ml_set_pixel_format(pixel_format)
        if not ret.success:
            raise RuntimeError(f"ml_set_pixel_format error, {ret.message}")

        ret = ml_mono.ml_move_nd_syn(nd)
        if not ret.success:
            raise RuntimeError(f"ml_move_nd_syn error, {ret.message}")

        ret = ml_mono.ml_set_exposure(exposure)
        if not ret.success:
            raise RuntimeError(f"ml_set_exposure error, {ret.message}")

        save_xlsx = save_path + "\\" + file_name
        wb = Workbook()
        wb.save(save_xlsx)
        wb = load_workbook(save_xlsx)
        wb.remove(wb["Sheet"])
        title = str("coefficient")
        ws = wb.create_sheet(title=title)
        line = []
        ws.append(line)
        line = []

        for i in range(avg_count):
            sph_coefficient = []
            cyl_coefficient = []
            last_sph = 0
            last_cyl = 0
            for sph in sph_list:
                rx = mlcm.pyRXCombination(sph=sph, cyl=0, axis=0)
                ret = ml_mono.ml_set_rx_syn(rx)
                if not ret.success:
                    raise RuntimeError(f"ml_set_rx_syn error, {ret.message}")

                ret = ml_mono.ml_capture_image_syn()
                if not ret.success:
                    raise RuntimeError(
                        f"ml_capture_image_syn error, {ret.message}")

                img = ml_mono.ml_get_image()
                X, Y, Z = cv2.split(img)  # type: ignore
                cv2.imwrite(os.path.join(
                    save_path, f"{mlcm.pyRXCombination_to_str(rx)}.tif"), Y)

                gray = cv2.mean(
                    Y[roi.y:roi.y+roi.height, roi.x:roi.x+roi.width])[0]
                sph_coefficient.append(gray)

                if sph == 0:
                    last_sph = gray
            for i in range(len(sph_coefficient)):
                sph_coefficient[i] = format(
                    sph_coefficient[i] / last_sph, ".3f")
            update_status("INFO", f"sph coefficient: {sph_coefficient}")
            line = ["sph_coefficient", *sph_coefficient]
            ws.append(line)
            line = []
            ws.append(line)
            line = []

            for cyl in cyl_list:
                rx = mlcm.pyRXCombination(sph=0, cyl=cyl, axis=0)
                ret = ml_mono.ml_set_rx_syn(rx)
                if not ret.success:
                    raise RuntimeError(f"ml_set_rx_syn error, {ret.message}")

                ret = ml_mono.ml_capture_image_syn()
                if not ret.success:
                    raise RuntimeError(
                        f"ml_capture_image_syn error, {ret.message}")

                img = ml_mono.ml_get_image()
                X, Y, Z = cv2.split(img)  # type: ignore
                cv2.imwrite(os.path.join(
                    save_path, f"{mlcm.pyRXCombination_to_str(rx)}.tif"), Y)
                gray = cv2.mean(
                    Y[roi.y:roi.y+roi.height, roi.x:roi.x+roi.width])[0]
                cyl_coefficient.append(gray)

                if cyl == 0:
                    last_cyl = gray
            for i in range(len(cyl_coefficient)):
                cyl_coefficient[i] = format(
                    cyl_coefficient[i] / last_cyl, ".3f")
            update_status("INFO", f"cyl coefficient: {cyl_coefficient}")
            print(cyl_coefficient)
            line = ["cyl_coefficient", *cyl_coefficient]
            ws.append(line)
            line = []
            ws.append(line)
            line = []

        wb.save(save_xlsx)
        update_status("INFO", "calculate sph cyl coefficient finish")
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg)
        raise
