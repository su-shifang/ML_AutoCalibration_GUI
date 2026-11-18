import mlcolorimeter as mlcm
from typing import List, Dict,Optional,Callable,Literal
import cv2
import os
from datetime import datetime
from typing import List
import pandas as pd

MsgLevel=Literal["INFO","WARN","ERROR"]
def datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]


def calculate_sph_cyl_coefficient(
        colorimeter: mlcm.ML_Colorimeter,
        sph_list: List[float],
        cyl_list: List[float],
        save_path: str,
        nd_list: List[mlcm.MLFilterEnum],
        xyz_list: List[mlcm.MLFilterEnum],
        roi: mlcm.pyCVRect,
        exposure_map_obj: Optional[Dict[mlcm.MLFilterEnum, Dict[mlcm.MLFilterEnum, mlcm.pyExposureSetting]]] = None,
        count: int = 10,
        pixel_format: mlcm.MLPixelFormat = mlcm.MLPixelFormat.MLMono12,
        status_callback: Optional[Callable[[MsgLevel,str], None]] = None
):
    run_time_tag = datetime_str() # 测试开始时生成一次时间戳，保证同一次测试多组文件时间戳一致
    def update_status(level: MsgLevel, message:str):
        msg=f"[{level}] {message}"
        if status_callback is not None:
            try:
                status_callback(level,msg)
            except Exception:
                # 回调出错不中断采集，降级打印到控制台
                print(msg)
        else:
            print(msg)
    try:
        update_status("INFO", f"calculate sph and cyl coefficient start")
        os.makedirs(save_path,exist_ok=True)
        if exposure_map_obj is None:
            raise ValueError("exposure_map_obj cannot be None, please provide exposure setting dict")
        module_id = 1
        ml_mono = colorimeter.ml_bino_manage.ml_get_module_by_id(module_id)
        ret = ml_mono.ml_set_pixel_format(pixel_format)
        if not ret.success:
            raise RuntimeError(f"ml_set_pixel_format error, msg: {ret.message}")
        def _scan_rx_sequence(rx_combo_list:List[mlcm.pyRXCombination])->Dict[float,float]:
            gray_map: Dict[float,float]={}
            ref_gray=0.0 # 0度基准灰度
            for rx in rx_combo_list:
                ret=ml_mono.ml_set_rx_syn(rx)
                if not ret.success:
                    raise RuntimeError(f"ml_set_rx_syn error, msg: {ret.message}")
                ret = ml_mono.ml_capture_image_syn()
                if not ret.success:
                    raise RuntimeError(f"ml_capture_image_syn error, msg: {ret.message}")
                
                img = ml_mono.ml_get_image()
                img_save_name=f'{mlcm.pyRXCombination_to_str(rx)}_{run_time_tag}.tif'
                cv2.imwrite(os.path.join(save_path,img_save_name),img)
                # ROI边界校验
                h,w=img.shape[:2]
                if roi.x+roi.width >w or roi.y+roi.height>h:
                    raise ValueError(f"ROI out of image range! img size({w},{h}), roi x,y,w,h={roi.x},{roi.y},{roi.width},{roi.height}")
                roi_img=img[roi.y : roi.y+roi.height, roi.x : roi.x+roi.width]
                gray_mean=cv2.mean(roi_img)[0]

                key = rx.sph if rx.cyl==0 else rx.cyl
                gray_map[key]=gray_mean
                if rx.sph==0 and rx.cyl==0:
                    ref_gray=gray_mean
            
            # 基准灰度检测
            if abs(ref_gray)<1e-6:
                update_status("WARN", f"Current ref gray = {ref_gray}, close to zero")
                raise RuntimeError("Reference gray value is zero, cannot compute ratio")
            
            # 计算比值，保留3位小数，浮点数
            ratio_map={k:round(v/ref_gray,3)for k,v in gray_map.items()}
            return ratio_map
        

        for nd in nd_list:
            ret = ml_mono.ml_move_nd_syn(nd)
            if not ret.success:
                raise RuntimeError(f"ml_move_nd_syn error, msg: {ret.message}")
            for xyz in xyz_list:
                ret = ml_mono.ml_move_xyz_syn(xyz)
                if not ret.success:
                    raise RuntimeError(f"ml_move_xyz_syn error, msg: {ret.message}")
                ret = ml_mono.ml_set_exposure(exposure_map_obj[nd][xyz])
                if not ret.success:
                    raise RuntimeError(f"ml_set_exposure error, msg: {ret.message}")
                sph_results = []
                cyl_results = []
                for loop_idx in range(count):
                    #========================sph coefficient calculation========================
                    rx_sph_list=[mlcm.pyRXCombination(sph=s,cyl=0,axis=0) for s in sph_list]
                    sph_ratio=_scan_rx_sequence(rx_sph_list)
                    sph_ratio["Cycle"]=loop_idx+1
                    sph_results.append(sph_ratio)
                    update_status("INFO",f"Cycle {loop_idx+1} sph coefficient: {sph_ratio} ")

                    #========================cyl coefficient calculation========================
                    rx_cyl_list=[mlcm.pyRXCombination(sph=0,cyl=c,axis=0) for c in cyl_list]
                    cyl_ratio=_scan_rx_sequence(rx_cyl_list)
                    cyl_ratio["Cycle"]=loop_idx+1
                    cyl_results.append(cyl_ratio)
                    update_status("INFO",f"Cycle {loop_idx+1} cyl coefficient: {cyl_ratio} ")
            df = pd.DataFrame(sph_results)
            sph_filename = f"sph_{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{run_time_tag}.xlsx"
            df.to_excel(os.path.join(save_path, sph_filename), index=False)
            
            df = pd.DataFrame(cyl_results)
            cyl_filename = f"cyl_{mlcm.MLFilterEnum_to_str(nd)}_{mlcm.MLFilterEnum_to_str(xyz)}_{run_time_tag}.xlsx"
            df.to_excel(os.path.join(save_path, cyl_filename), index=False)
            update_status("INFO",f"ND:{mlcm.MLFilterEnum_to_str(nd)} XYZ:{mlcm.MLFilterEnum_to_str(xyz)} save finish")

        update_status("INFO", "calculate sph cyl coefficient finish")
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg=f"{type(e).__name__}: {str(e)}"
        update_status("ERROR",err_msg)
        raise

if __name__ == "__main__":
    eye1_path = r"E:\config\EYE1"
    save_path=r'D:\sph_cyl_coefficient'
    path_list = [
        eye1_path,
    ]
    try:
        # create a ML_Colorimeter system instance
        ml_colorimeter = mlcm.ML_Colorimeter()
        # add mono module into ml_colorimeter system, according to path_list create one or more mono module
        ret = ml_colorimeter.ml_add_module(path_list=path_list)
        if not ret.success:
            raise RuntimeError(f"[ERROR] ml_add_module error, msg: {ret.message}")
        # connect all module in the ml_colorimeter system
        ret = ml_colorimeter.ml_connect()
        if not ret.success:
            raise RuntimeError(f"[ERROR] ml_connect error, msg: {ret.message}")
        
        nd_list = [mlcm.MLFilterEnum.ND0]
        xyz_list = [mlcm.MLFilterEnum.X]
        exposure_map_obj = {
            mlcm.MLFilterEnum.ND0: {
                mlcm.MLFilterEnum.X: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=21
                ),
                mlcm.MLFilterEnum.Y: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=21
                ),
                mlcm.MLFilterEnum.Z: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=21
                ),
            },
            mlcm.MLFilterEnum.ND1: {
                mlcm.MLFilterEnum.X: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=21
                ),
                mlcm.MLFilterEnum.Y: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=21
                ),
                mlcm.MLFilterEnum.Z: mlcm.pyExposureSetting(
                    exposure_mode=mlcm.ExposureMode.Fixed, exposure_time=21
                ),
            },
        }

        avg_count = 10
        sph_list = [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4]
        cyl_list = [-4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0]

        roi = mlcm.pyCVRect(0, 0, 300, 300)


        calculate_sph_cyl_coefficient(
            colorimeter=ml_colorimeter,
            sph_list=sph_list,
            cyl_list=cyl_list,
            save_path=save_path,
            nd_list=nd_list,
            xyz_list=xyz_list,
            roi=roi,
            exposure_map_obj=exposure_map_obj,
            count=avg_count,
            pixel_format=mlcm.MLPixelFormat.MLMono12
        )
    except Exception as e:
        print(f"[ERROR] {e}")
