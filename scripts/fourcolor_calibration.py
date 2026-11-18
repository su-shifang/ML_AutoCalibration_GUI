import sys
import mlcolorimeter as mlcm
from typing import Dict,Literal,Callable,Optional
import os
"""
Four-Color Calibration Example

Performs four-color calibration in two stages:
1. Capture: for each ND filter and light source (R/G/B/W), captures and
   averages images to compute the M matrix, saves the M matrix and exposure.
2. Calculate: computes the N matrix from
   NMatrix_xyL.json, then derives and saves the R matrix.

Note: light source switching must be handled externally (or by added code).

Usage: python fourcolor_calibration.py
"""
MsgLevel = Literal["INFO", "WARN", "ERROR"]

def update_status(
        level: MsgLevel, 
        message: str,
        status_callback: Optional[Callable[[MsgLevel, str], None]] = None
    ):
    msg = f"[{level}] {message}"
    if status_callback is not None:
        try:
            status_callback(level, msg)
        except Exception:
            # 回调出错不中断采集，降级打印到控制台
            print(msg)
    else:
        print(msg)

def fourcolor_calibration_capture(
        auto_cali: mlcm.pyMLAutoCalibration,
        ml_mono: mlcm.pyMLMonoBusinessManage,
        binn_selector:mlcm.BinningSelector,
        binn_mode:mlcm.BinningMode,
        binn:mlcm.Binning,
        pixel_format:mlcm.MLPixelFormat,
        save_path: str,
        light_source: str,
        nd: mlcm.MLFilterEnum,
        avg_count: int = 5,
        exposure_map: Optional[Dict[mlcm.MLFilterEnum, mlcm.pyExposureSetting]] = None,
        roi: mlcm.pyCVRect = mlcm.pyCVRect(),
        is_do_ffc: bool = False,
        status_callback: Optional[Callable[[MsgLevel, str], None]] = None

):
    try:
        os.makedirs(save_path,exist_ok=True)
        if exposure_map is None:
            exposure_map = {
                mlcm.MLFilterEnum.X: mlcm.pyExposureSetting(),
                mlcm.MLFilterEnum.Y: mlcm.pyExposureSetting(),
                mlcm.MLFilterEnum.Z: mlcm.pyExposureSetting(),
            }
        # set pixel format to MLMono12 during capture
        ret = ml_mono.ml_set_pixel_format(pixel_format)
        if not ret.success:
            raise RuntimeError(f"ml_set_pixel_format error, msg: {ret.message}")
        ret = ml_mono.ml_set_binning_selector(binn_selector)
        if not ret.success:
            raise RuntimeError(f"ml_set_binning_selector error, msg: {ret.message}")

        # Set binning mode for camera.
        ret = ml_mono.ml_set_binning_mode(binn_mode)
        if not ret.success:
            raise RuntimeError(f"ml_set_binning_mode error, msg: {ret.message}")
        
        ret = ml_mono.ml_set_binning(binn)
        if not ret.success:
            raise RuntimeError(f"ml_set_binning error, msg: {ret.message}")
        
        rx = mlcm.pyRXCombination(0, 0, 0)
        ret = ml_mono.ml_set_rx_syn(rx=rx)
        if not ret.success:
            raise RuntimeError(f"ml_set_rx_syn error, msg: {ret.message}")
        rx.sph=sys.float_info.max

        mMatrixCaptureSetting = mlcm.pyMMatrixCaptureSetting(
            savePath=save_path,
            lightsource=light_source,
            ndfilter=nd,
            colorfilterExposureMap=exposure_map,
            rx=rx,
            avgCount=avg_count,
            roi=roi,
            applyFFC=is_do_ffc,
            isColorCamera=False
        )

        mMatrixExposureSaveSetting = mlcm.pyMMatrixExposureSaveSetting(
            savePath=save_path,
            aperture=ml_mono.ml_get_aperture(),
            ndfilter=nd,
            rx=rx
        )

        update_status("INFO", f"ND={mlcm.MLFilterEnum_to_str(nd)} Light={light_source}: start fourcolor calibration: capture images and compute Mmatrix",status_callback)
        ret = auto_cali.ml_capture_images_and_compute_mmatrix(
            setting=mMatrixCaptureSetting)
        if not ret.success:
            raise RuntimeError(f"ND={mlcm.MLFilterEnum_to_str(nd)} Light={light_source}: ml_capture_images_and_compute_mmatrix error, msg: {ret.message}")
        update_status("INFO", f"ND={mlcm.MLFilterEnum_to_str(nd)} Light={light_source}: capture images and compute Mmatrix finish",status_callback)

        ret = auto_cali.ml_save_mmatrix_and_et(setting=mMatrixExposureSaveSetting)
        if not ret.success:
            raise RuntimeError(f"ND={mlcm.MLFilterEnum_to_str(nd)} Light={light_source}: ml_save_mmatrix_and_et error, msg: {ret.message}")
        update_status("INFO", f"ND={mlcm.MLFilterEnum_to_str(nd)} Light={light_source}: save Mmatrix and exposure time finish",status_callback)
        
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"ND={mlcm.MLFilterEnum_to_str(nd)} Light={light_source} | {type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg,status_callback)
        raise


def fourcolor_calibration_calculate(
        auto_cali: mlcm.pyMLAutoCalibration,
        nMatrix_path: str,
        nd: mlcm.MLFilterEnum,
        status_callback: Optional[Callable[[MsgLevel, str], None]] = None
):
    try:
        # get M matrix
        mmatrix = auto_cali.ml_get_mmatrix()
        update_status("INFO", f"ND={mlcm.MLFilterEnum_to_str(nd)} | MMatrix loaded: {mmatrix}", status_callback)

        # calculate N matrix using the input NMatrix_xyL.json
        ret = auto_cali.ml_compute_nmatrix(nmatrixJsonPath=nMatrix_path)
        if not ret.success:
            raise RuntimeError(f"ml_compute_nmatrix error, msg: {ret.message}")
        update_status("INFO", f"ND={mlcm.MLFilterEnum_to_str(nd)} | N matrix compute finish", status_callback)

        # get N matrix
        nmatrix = auto_cali.ml_get_nmatrix()
        update_status("INFO", f"ND={mlcm.MLFilterEnum_to_str(nd)} | NMatrix: {nmatrix}", status_callback)

        # calculate R matrix using the M matrix and N matrix, and save R matrix to config
        ret = auto_cali.ml_compute_rmatrix(ndfilter=nd)
        if not ret.success:
            raise RuntimeError(f"ml_compute_rmatrix error, msg: {ret.message}")
        update_status("INFO", f"ND={mlcm.MLFilterEnum_to_str(nd)} | R matrix compute finish", status_callback)

        ret = auto_cali.ml_save_rmatrix(ndfilter=nd)
        if not ret.success:
            raise RuntimeError(f"ml_save_rmatrix error, msg: {ret.message}")
        update_status("INFO", f"ND={mlcm.MLFilterEnum_to_str(nd)} | R matrix saved", status_callback)

        # get R matrix
        rmatrix = auto_cali.ml_get_rmatrix()
        update_status("INFO", f"ND={mlcm.MLFilterEnum_to_str(nd)} | RMatrix: {rmatrix}", status_callback)
    except Exception as e:
        err_msg = f"ND={mlcm.MLFilterEnum_to_str(nd)} | {type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg, status_callback)
        raise


if __name__ == "__main__":
    # set mono module calibration configuration path
    eye1_path = r"D:\MLOptic\MLColorimeter\weilaixing\EYE1"
    path_list = [
        eye1_path,
    ]
    module_id=1
    binn_selector=mlcm.BinningSelector.Logic,
    binn_mode=mlcm.BinningMode.AVERAGE,
    binn=mlcm.Binning.ONE_BY_ONE,
    pixel_format=mlcm.MLPixelFormat.MLMono12
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
        
        ml_mono = ml_colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
        auto_cali = mlcm.pyMLAutoCalibration(ml_mono)

        # N matrix path, NMatrix_xyL.json contains the specbos data of your light source
        NMatrix_path = r"E:\testout\NMatrix_xyL.json"
        # path to save M images and exposure time
        save_path = r"E:\testout"

        # nd filter list to switch during capture
        nd_list = [mlcm.MLFilterEnum.ND0]
        # exposure map of color filter during capture
        exposure_map = {
            mlcm.MLFilterEnum.X: mlcm.pyExposureSetting(
                exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100
            ),
            mlcm.MLFilterEnum.Y: mlcm.pyExposureSetting(
                exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100
            ),
            mlcm.MLFilterEnum.Z: mlcm.pyExposureSetting(
                exposure_mode=mlcm.ExposureMode.Auto, exposure_time=100
            ),
        }
        # count to calculate average image for one color filter
        avg_count = 1
        # ROI setting to calculate M matrix
        roi = mlcm.pyCVRect(x=5632, y=4600, width=500, height=500)
        # whether to do flat field correction before calculation
        is_do_ffc = False
        # light source list for fourcolor calibration
        light_source_list = ["R", "G", "B", "W"]

        # capture M matrix image for nd list
        for nd in nd_list:
            # need to manually switch the light source of IS, or add your code to control the IS
            for light_source in light_source_list:
                # execute fourcolor calibration capture
                fourcolor_calibration_capture(
                    auto_cali=auto_cali,
                    ml_mono=ml_mono,
                    binn_selector=binn_selector,
                    binn_mode=binn_mode,
                    binn=binn,
                    pixel_format=pixel_format,
                    save_path=save_path,
                    light_source=light_source,
                    nd=nd,
                    avg_count=avg_count,
                    exposure_map=exposure_map,
                    roi=roi,
                    is_do_ffc=is_do_ffc,
                )
            print(
                "capture fourcolor calibration images for "
                + mlcm.MLFilterEnum_to_str(nd)
            )

            # calculate M, N, R matrix after capturing M matrix
            fourcolor_calibration_calculate(
                auto_cali=auto_cali,
                nd=nd,
                nMatrix_path=NMatrix_path,
            )
            print("calculate R matrix for " + mlcm.MLFilterEnum_to_str(nd))

    except Exception as e:
        print(e)
