import cv2
from cv2 import blur
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import csv
import os
from typing import List, Dict, Tuple, Literal, Optional, Callable
import mlcolorimeter as mlcm
from datetime import datetime
import matplotlib
matplotlib.use('Agg')

MsgLevel = Literal["INFO", "WARN", "ERROR"]


def datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]


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


def get_FFC(filepath, loop, size: int):
    srcX = np.array(Image.open(os.path.join(
        filepath, f"{str(loop)}0%_ND0_X_FFC.tif")))
    srcY = np.array(Image.open(os.path.join(
        filepath, f"{str(loop)}0%_ND0_Y_FFC.tif")))
    srcZ = np.array(Image.open(os.path.join(
        filepath, f"{str(loop)}0%_ND0_Z_FFC.tif")))

    srcX = blur(srcX, (size, size))
    srcY = blur(srcY, (size, size))
    srcZ = blur(srcZ, (size, size))

    return [srcX, srcY, srcZ]


def FFC_calculate(
        xyz_list: List[str],
        filepath: str,
        binning: str,
        vrange: Dict[int, Tuple[int, int]],
        half_size: int,
        roi_list: List[mlcm.pyCVRect],
        status_callback:  Optional[Callable[[MsgLevel, str], None]] = None
):
    try:
        run_time_tag = datetime_str()
        update_status("INFO", f"FFC calculate {binning} start..., run_time_tag: {run_time_tag}",
                      status_callback)
        csv_name = ""
        size = 5
        prefix = ""
        if binning == "ONE_BY_ONE":
            prefix = "FFC_1X1"
            csv_name = f"FFC_1X1_{run_time_tag}.csv"
            size = 15
        elif binning == "TWO_BY_TWO":
            prefix = "FFC_2X2"
            csv_name = f"FFC_2X2_{run_time_tag}.csv"
            size = 10
        elif binning == "FOUR_BY_FOUR":
            prefix = "FFC_4X4"
            csv_name = f"FFC_4X4_{run_time_tag}.csv"
            size = 5

        csv_path = os.path.join(filepath, csv_name)
        with open(csv_path, "a+", newline="") as f:
            mywriter = csv.writer(f)
            mywriter.writerow(
                ["Gray Value", "Color Filter", "1", "2", "3",
                    "4", "5", "6", "7", "8", "9", "Uniformity"]
            )
        for loop_i, value in vrange.items():
            img_list = get_FFC(filepath, loop_i, size)
            for i in range(len(xyz_list)):
                row, col = img_list[i].shape[0], img_list[i].shape[1]
                center_row, center_col = int(row / 2), int(col / 2)
                fig = plt.figure(figsize=(16, 4))
                plt.subplot(1, 2, 1)
                plt.imshow(img_list[i], cmap="jet",
                           vmin=value[0], vmax=value[1])
                plt.xlabel("Col(pixel)")
                plt.ylabel("Row(pixel)")
                plt.colorbar(label="(FFC)")
                plt.title(f"{prefix} " +
                          xyz_list[i] + " " + str(loop_i) + "0%")
                plt.subplot(1, 2, 2)
                plt.plot(
                    img_list[i][center_row,
                                (center_col - half_size): (center_col + half_size)]
                )
                plt.plot(
                    img_list[i][(center_row - half_size)
                                 : (center_row + half_size), center_col]
                )
                line = []
                line.append(str(loop_i) + "0%")
                line.append(xyz_list[i])
                gray_list = []
                for roi in roi_list:
                    roi.x = max(0, roi.x)
                    roi.y = max(0, roi.y)
                    roi_y_end = roi.y+roi.height
                    roi_x_end = roi.x+roi.width
                    roi_x_end = min(roi_x_end, col)
                    roi_y_end = min(roi_y_end, row)
                    if roi.x < roi_x_end and roi.y < roi_y_end:
                        img_roi = img_list[i][roi.y:roi_y_end, roi.x:roi_x_end]
                        gray = cv2.mean(img_roi)[0]
                        gray_list.append(gray)
                        line.append(gray)
                    else:
                        update_status(
                            "ERROR", f"ROI 超出图像边界，图像索引: {i}, ROI: ({roi.x}, {roi.y}, {roi.width}, {roi.height})", status_callback)
                        return
                avg = np.mean(gray_list)
                val_max = np.max(gray_list)
                val_min = np.min(gray_list)

                uniformity = 1 - 0.5 * (val_max - val_min) / avg
                line.append(uniformity)
                with open(csv_path, "a+", newline="") as f:
                    mywriter = csv.writer(f)
                    mywriter.writerow(line)

                plt.grid(which="both")
                plt.xlabel("Position(pixel)")
                plt.ylabel("gray value")
                plt.ylim([value[0], value[1]])
                plt.legend(["Along-Col", "Along-Row"])
                img_path = os.path.join(
                    filepath, f"IS_0mm {prefix}_{str(loop_i)}0%_{xyz_list[i]}.png")
                plt.savefig(img_path, bbox_inches="tight")
                plt.close(fig)
                update_status("INFO", f"{img_path} 保存完成", status_callback)
            update_status("INFO", f"{loop_i}0%对应的ffc计算结束", status_callback)
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status("ERROR", err_msg, status_callback)
        raise


if __name__ == "__main__":
    filepath = r"E:\output\W\1binn"
    savepath = filepath
    if not os.path.exists(savepath):
        os.makedirs(savepath)
    xyz_list = ["X", "Y", "Z"]
    binning = "ONE_BY_ONE"

    vrange = {
        # 5: (1700, 2200),
        8: (2000, 3500),
        # 9: (3000, 3900)
    }
    # FOUR_BY_FOUR
    # roi_list = [
    #     mlcm.pyCVRect(750, 658, 200, 200),
    #     mlcm.pyCVRect(750, 1158, 200, 200),
    #     mlcm.pyCVRect(750, 1658, 200, 200),
    #     mlcm.pyCVRect(1350, 658, 200, 200),
    #     mlcm.pyCVRect(1350, 1158, 200, 200),
    #     mlcm.pyCVRect(1350, 1658, 200, 200),
    #     mlcm.pyCVRect(1950, 658, 200, 200),
    #     mlcm.pyCVRect(1950, 1158, 200, 200),
    #     mlcm.pyCVRect(1950, 1658, 200, 200),
    # ]
    # TWO_BY_TWO
    # roi_list = [
    #     mlcm.pyCVRect(1500, 1316, 400, 400),
    #     mlcm.pyCVRect(1500, 2316, 400, 400),
    #     mlcm.pyCVRect(1500, 3316, 400, 400),
    #     mlcm.pyCVRect(2700, 1316, 400, 400),
    #     mlcm.pyCVRect(2700, 2316, 400, 400),
    #     mlcm.pyCVRect(2700, 3316, 400, 400),
    #     mlcm.pyCVRect(3900, 1316, 400, 400),
    #     mlcm.pyCVRect(3900, 2316, 400, 400),
    #     mlcm.pyCVRect(3900, 3316, 400, 400),
    # ]
    # ONE_BY_ONE
    roi_list = [
        mlcm.pyCVRect(3000, 2632, 400, 400),
        mlcm.pyCVRect(3000, 4632, 400, 400),
        mlcm.pyCVRect(3000, 6632, 400, 400),
        mlcm.pyCVRect(5400, 2632, 400, 400),
        mlcm.pyCVRect(5400, 4632, 400, 400),
        mlcm.pyCVRect(5400, 6632, 400, 400),
        mlcm.pyCVRect(7800, 2632, 400, 400),
        mlcm.pyCVRect(7800, 4632, 400, 400),
        mlcm.pyCVRect(7800, 6632, 400, 400),
    ]
    # 根据FOV修改
    half_size = 3600
    FFC_calculate(
        xyz_list=xyz_list,
        filepath=filepath,
        vrange=vrange,
        binning=binning,
        half_size=half_size,
        roi_list=roi_list
    )
