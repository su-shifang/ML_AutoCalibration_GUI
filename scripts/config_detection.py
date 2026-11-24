
import os
import configparser
import pandas as pd
import json
from PIL import Image
import itertools
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from typing import List, Literal, Optional, Callable, Tuple, Dict
from datetime import datetime

MsgLevel = Literal["INFO", "WARN", "ERROR"]


def datetime_str():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]


def get_subfolder_name(base_path):
    subfolder_names = []
    for entry in os.listdir(base_path):
        entry_path = os.path.join(base_path, entry)
        if os.path.isdir(entry_path):
            subfolder_names.append(entry)
    return subfolder_names


def validate_folder_structure(folder_structure, level_expected, has_subfolder_rule):
    sub_levels = [p for p in folder_structure[1:] if p.strip() != ""]
    if not has_subfolder_rule:
        return len(sub_levels) == 0, ""
    expected_depth = len(level_expected)
    actual_depth = len(sub_levels)
    if actual_depth < expected_depth:
        return False, f"目录层级不足, 需要至少{expected_depth}层"
    for start_idx in range(actual_depth - expected_depth + 1):
        window = sub_levels[start_idx: start_idx + expected_depth]
        match = True
        for i in range(expected_depth):
            if window[i] not in level_expected[i]:
                match = False
                break
        if match:
            # 匹配成功后，检查窗口后面是否还有剩余文件夹
            remain = sub_levels[start_idx + expected_depth:]
            if len(remain) == 0:
                # 无多余层级，匹配成功
                return True, ""
            else:
                return False, f"匹配到规则目录, 但存在多余子层级: {'/'.join(remain)}"
    return False, "没有找到匹配Folder_Rule的目录"


def gen_diopter_folder_names(sph_list: List[float], cyl_list: List[float], axis_list: List[int]) -> List[str]:
    '''生成屈光度文件夹名称列表'''
    name_list = []
    for sph, cyl, axis in itertools.product(sph_list, cyl_list, axis_list):
        if sph == 0:
            name_list.append(f"{sph}d_{cyl}d_{axis}deg")
        else:
            name_list.append(f"{sph}d_0d_0deg")
    name_list.append('Mean')
    return name_list


def parse_mapping(raw_str: str):
    '''解析ini逗号分隔字符串，自动去除.0，如-8.0 → -8；-4.5保留-4.5'''
    if not raw_str or raw_str.strip() == "":
        return []
    parts = [p.strip() for p in raw_str.split(",") if p.strip()]
    res = []
    for p in parts:
        val = float(p)
        if val.is_integer():
            res.append(int(val))
        else:
            res.append(val)
    return res


def parse_folder_rule_and_generate_expected(section_name: str, cfg: configparser.ConfigParser, rule_map) -> Tuple[List[List[str]], List[str], str, bool]:
    sec = cfg[section_name]
    folder_rule = sec.get("Folder_Rule", "").strip()
    has_RX = "rx" in folder_rule.lower()
    if has_RX:
        sphere_list = parse_mapping(sec.get("Sphere_Mapping", ""))
        cylinder_list = parse_mapping(sec.get("Cylinder_Mapping", ""))
        axis_list = parse_mapping(sec.get("Axis_Mapping", ""))
    else:
        sphere_list = []
        cylinder_list = []
        axis_list = []
    has_diopter = len(sphere_list) > 0 and len(
        cylinder_list) > 0 and len(axis_list) > 0
    diopter_names = gen_diopter_folder_names(
        sphere_list, cylinder_list, axis_list) if has_diopter else []
    level_expected = []
    result_flat = []
    if not folder_rule:
        if has_diopter:
            level_expected.append(diopter_names)
            result_flat = diopter_names
            has_subfolder_rule = True
        else:
            has_subfolder_rule = False
        return level_expected, result_flat, folder_rule, has_subfolder_rule

    # 取出当前section独立的规则
    section_rule = rule_map.get(section_name, {})
    rule_levels = [item for item in folder_rule.split(
        "/") if item.strip() != ""]
    for level_rule in rule_levels:
        keys = level_rule.split("_")
        lists_to_combine = []
        for k in keys:
            if k in section_rule:
                lists_to_combine.append(section_rule[k])
        if not lists_to_combine:
            continue
        combinations = list(itertools.product(*lists_to_combine))
        level_names = ["_".join(items) for items in combinations]
        level_expected.append(level_names)
        result_flat.extend(level_names)
    if has_diopter:
        level_expected.append(diopter_names)
        result_flat.extend(diopter_names)
    has_subfolder_rule = True
    return level_expected, result_flat, folder_rule, has_subfolder_rule


def gather_file_data(base_path, folder_names, config, rule_map, width=None, height=None, status_callback: Optional[Callable[[str], None]] = None):
    data = []
    # 每个folder独立计数器
    dir_count = 0
    file_count = 0

    def recursive_search(current_path, folder, current_level_stack: List[List[str]], full_level_expected: List[List[str]], result_flat: List[str], folder_rule: str, has_subfolder_rule: bool, suffix: str):
        nonlocal width, height, dir_count, file_count
        current_level_list = current_level_stack[0] if len(
            current_level_stack) > 0 else None
        remain_levels = current_level_stack[1:] if len(
            current_level_stack) > 1 else []
        for entry in os.listdir(current_path):
            entry_path = os.path.join(current_path, entry)
            if os.path.isdir(entry_path):
                dir_count += 1
                # 两层命名规则
                if len(full_level_expected) == 2:
                    if len(current_level_stack) == 2:
                        # 当前匹配第一层
                        if entry in level_expected1:
                            if entry not in found_map:
                                found_map[entry] = set()
                            # 进入第一层目录，递归，剩下层级是第二层
                            recursive_search(entry_path, folder, remain_levels, full_level_expected,
                                             result_flat, folder_rule, has_subfolder_rule, suffix)
                    # 当前进入第二层，收集第二层目录
                    elif len(current_level_stack) == 1:
                        parent_dir_name = os.path.basename(current_path)
                        if parent_dir_name in found_map:
                            if entry in level_expected2:
                                found_map[parent_dir_name].add(entry)
                        recursive_search(entry_path, folder, remain_levels, full_level_expected,
                                         result_flat, folder_rule, has_subfolder_rule, suffix)
                    else:
                        recursive_search(entry_path, folder, remain_levels, full_level_expected,
                                         result_flat, folder_rule, has_subfolder_rule, suffix)
                # 单层规则
                elif len(full_level_expected) == 1:
                    if len(current_level_stack) == 1:
                        if entry in level_expected1:
                            found_map[entry] = set()
                    recursive_search(entry_path, folder, remain_levels, full_level_expected,
                                     result_flat, folder_rule, has_subfolder_rule, suffix)
                else:
                    # 无目录规则
                    recursive_search(entry_path, folder, remain_levels, full_level_expected,
                                     result_flat, folder_rule, has_subfolder_rule, suffix)

            elif os.path.isfile(entry_path):
                relative_path = os.path.relpath(entry_path, base_path)
                folder_structure = os.path.dirname(relative_path).split(os.sep)
                file_content = ""
                value = ""
                file_count += 1
                if entry.endswith('.json'):
                    file_content = read_json_content(entry_path)
                    if folder in ["ColorShift", "Luminance", "Radiance"]:
                        x_offset, y_offset = validate_json_format(
                            folder, file_content)
                        if folder == 'ColorShift':
                            value = f"x_offset: {x_offset}, y_offset: {y_offset}"
                        elif folder in ("Luminance", "Radiance"):
                            value = f"k: {x_offset}, b: {y_offset}"
                    elif folder == 'Offset':
                        x_offset, y_offset = validate_json_format_Offset(
                            file_content)
                        value = f"ExposureOffset: {x_offset}, GrayOffset: {y_offset}"
                    file_content = json.dumps(
                        file_content, indent=4, ensure_ascii=False)
                elif entry.lower().endswith(('.tif', '.tiff')):
                    if folder == 'Dark':
                        try:
                            with Image.open(entry_path) as img:
                                width, height = img.size
                                file_content = f"图像有效, size: {img.size}"
                        except (IOError, SyntaxError):
                            raise RuntimeError(
                                f"File {entry_path} is corrupted. Please fix the image and try again.")
                    else:
                        try:
                            with Image.open(entry_path) as img:
                                img.load()
                                if img.size == (0, 0) or img.getbbox() is None:
                                    file_content = "没有有效像素"
                                elif width is not None and (img.width != width or img.height != height):
                                    file_content = f"图像尺寸与Dark图像不匹配, expected: ({width}, {height}), actual: ({img.width}, {img.height})"
                                else:
                                    file_content = f"图像有效, size: {img.size}"
                        except (IOError, SyntaxError):
                            file_content = "图像损坏"
                    value = ""

                elif entry.lower() in ['thumbs.db']:
                    continue  # 跳过Thumbs.db文件
                else:
                    file_content = "非json或tif文件, 未读取内容"
                    value = ""
                reason = ""  # 默认为空，pass时为空
                folder_ok, folder_err_msg = validate_folder_structure(
                    folder_structure, full_level_expected, has_subfolder_rule)
                if not has_subfolder_rule and suffix.strip() == "":
                    if folder_ok:
                        status = 'pass'
                        reason = ""
                    else:
                        status = 'loss'
                        reason = folder_err_msg
                else:
                    if folder_structure[-1] == "Mean":
                        suffix_ok = True
                    else:
                        suffix_ok = (entry == suffix.strip())
                    if folder_ok and suffix_ok:
                        status = 'pass'
                        reason = ""
                    else:
                        status = 'loss'
                        err_list = []
                        if not folder_ok:
                            err_list.append(folder_err_msg)
                        if not suffix_ok:
                            err_list.append(f"文件名不满足{suffix}")
                        reason = ", ".join(err_list)
                # 日志输出loss信息
                if status == 'loss':
                    update_status(
                        f"❌ {entry_path} | status: {status} | reason: {reason}", status_callback)
                elif status == 'pass':
                    update_status(
                        f"✅ {entry_path} | status: {status}", status_callback)
                data.append([folder_rule] + folder_structure + [entry] +
                            [file_content] + [value] + [reason] + [status])

    # ==========EYE1根目录json校验==========
    eye1_json_dict = {}
    for entry in os.listdir(base_path):
        entry_path = os.path.join(base_path, entry)
        if os.path.isfile(entry_path) and entry.endswith('.json'):
            eye1_json_dict[entry] = entry_path
    motion_name = "MotionConfig.json"
    diopter_name = "DiopterScanConfig.json"
    focus_name = "FocusScanConfig.json"
    check_status = 'pass'
    check_msg = ''
    if motion_name in eye1_json_dict:
        # MotionConfig存在，则另外两个必须存在
        if diopter_name not in eye1_json_dict or focus_name not in eye1_json_dict:
            check_status = 'loss'
            missing = []
            if diopter_name not in eye1_json_dict:
                missing.append(diopter_name)
            if focus_name not in eye1_json_dict:
                missing.append(focus_name)
            check_msg = f"MotionConfig存在, 但缺少文件: {', '.join(missing)}"
        else:
            # 读取三个json文件并校验
            try:
                motion_data = read_json_content(eye1_json_dict[motion_name])
                diopter_data = read_json_content(eye1_json_dict[diopter_name])
                focus_data = read_json_content(eye1_json_dict[focus_name])
                ok, msg = check_infinity_position(
                    motion_data, diopter_data, focus_data)
                if ok:
                    check_status = 'pass'
                else:
                    check_status = 'loss'
                check_msg = msg
            except Exception as e:
                check_status = 'loss'
                check_msg = f"读取或校验json文件失败: {e}"
    else:
        # MotionConfig不存在，不能出现另外两个文件
        has_extra = []
        if diopter_name in eye1_json_dict:
            has_extra.append(diopter_name)
        if focus_name in eye1_json_dict:
            has_extra.append(focus_name)
        if len(has_extra) > 0:
            check_status = 'loss'
            check_msg = f"MotionConfig不存在, 但出现多余文件: {', '.join(has_extra)}"
        else:
            check_status = 'pass'
            check_msg = 'MotionConfig不存在, 其他两个文件也不存在'
    # 日志打印json校验结果
    if check_status == 'pass':
        update_status(
            f"✅ EYE1根目录json校验 | status: {check_status}", status_callback)
    else:
        update_status(
            f"❌ EYE1根目录json校验 | status: {check_status} | reason: {check_msg}", status_callback)

    for json_filename, json_path in eye1_json_dict.items():
        file_content = read_json_content(json_path)
        json_str = json.dumps(file_content, ensure_ascii=False, indent=4)
        # 如果是三个目标配置文件, 填入校验信息, 普通json留空
        if json_filename in [motion_name, diopter_name, focus_name]:
            data.append(['EYE1', json_filename, json_str,
                        "", check_msg, check_status])
        else:
            data.append(['EYE1', json_filename, json_str, "", "", 'pass'])

    for folder in folder_names:
        update_status(f"🔍 [SCAN] 开始扫描文件夹: {folder}", status_callback)
        folder_path = os.path.join(base_path, folder)
        if not os.path.exists(folder_path):
            msg = f"模块文件夹不存在：{folder}"
            update_status(msg, status_callback)
            continue
        # 每个folder扫描前重置计数器
        dir_count = 0
        file_count = 0
        if folder in config.sections():
            sec = config[folder]
            suffix = sec.get("Suffix", "").strip()
            level_expected, result_flat, folder_rule, has_subfolder_rule = parse_folder_rule_and_generate_expected(
                folder, config, rule_map)
        else:
            level_expected = []
            result_flat = []
            suffix = ""
            has_subfolder_rule = False
            folder_rule = ""

        # 分层收集目录，包括两层目录情况
        # key表示第一层目录名，value为第一层下找到的第二层子目录集合
        found_map: Dict[str, set] = {}
        # 第一层预期目录列表
        level_expected1 = level_expected[0] if len(level_expected) > 0 else []
        level_expected2 = level_expected[1] if len(level_expected) > 1 else []

        recursive_search(folder_path, folder, level_expected, level_expected,
                         result_flat, folder_rule, has_subfolder_rule, suffix)
        data.append(['', '', '', '', '', '', ''])

        # 文件夹数量校验汇总
        summary_status = "pass"
        summary_msg_list = []
        # 第一层统计
        level1_expected_set = set(level_expected1)
        level1_found_set = set(found_map.keys())
        level1_missing = level1_expected_set-level1_found_set
        level1_extra = level1_found_set-level1_expected_set
        summary_msg_list.append(
            f"【第一层目录】预期:{len(level1_expected_set)}个，实际找到:{len(level1_found_set)}个")
        if level1_missing:
            summary_status = "loss"
            summary_msg_list.append(
                f"第一层缺失：{', '.join(sorted(level1_missing))}")
        if level1_extra:
            summary_status = "loss"
            summary_msg_list.append(f"第一层多余：{', '.join(sorted(level1_extra))}")
        # 遍历已经找到的第一层，统计第二层，第一层缺失的不处理
        for l1_name, l1_found_l2 in found_map.items():
            l2_expected_set = set(level_expected2)
            l2_missing = l2_expected_set-l1_found_l2
            l2_extra = l1_found_l2-l2_expected_set
            summary_msg_list.append(
                f"└ [{l1_name}] 第二层预期{len(l2_expected_set)}，实际找到{len(l1_found_l2)}")
            if l2_missing:
                summary_status = "loss"
                summary_msg_list.append(
                    f"    ├ 缺失：{', '.join(sorted(l2_missing))}")
            if l2_extra:
                summary_status = "loss"
                summary_msg_list.append(
                    f"    ├ 多余：{', '.join(sorted(l2_extra))}")

        summary_reason = "\n".join(summary_msg_list)

        # 把汇总行写入data，放到当前模块的末尾
        data.append([f"[{folder}目录汇总]", "", "", "", "",
                    summary_reason, summary_status])
        data.append(['', '', '', '', '', '', ''])
        update_status(f"✅ [SCAN_END] 扫描完成: {folder}", status_callback)
        update_status(
            f"📊 [STAT] {folder} 统计：遍历子文件夹={dir_count} 个，全部文件数量={file_count} 个", status_callback)
        update_status(f"📂【目录完整性检查】\n{summary_reason}", status_callback)
    return data


def read_json_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception:
        return "Error reading file: file format error"


def check_infinity_position(motion_cfg: dict, diopter_cfg: dict, focus_cfg: dict) -> Tuple[bool, str]:
    """
    校验三个配置文件的InfinityPosition
    返回 (是否pass, 提示信息)
    """
    if "MotionMap" not in motion_cfg:
        return False, "MotionConfig 缺少 MotionMap 字段"
    motion_map_list = motion_cfg["MotionMap"]
    if not isinstance(motion_map_list, list) or len(motion_map_list) == 0:
        return False, "MotionConfig.MotionMap 为空数组"
    motion_item = motion_map_list[0]
    if "InfinityPosition" not in motion_item:
        return False, "MotionConfig.MotionMap[0] 缺少 InfinityPosition 字段"
    if "InfinityPosition" not in diopter_cfg:
        return False, "DiopterScanConfig 缺少 InfinityPosition 字段"
    if "InfinityPosition" not in focus_cfg:
        return False, "FocusScanConfig 缺少 InfinityPosition 字段"

    diopter_min = diopter_cfg["DiopterMin"]
    diopter_max = diopter_cfg["DiopterMax"]
    if diopter_min > diopter_max:
        return False, f"DiopterScanConfig.DiopterMin({diopter_min}) > DiopterScanConfig.DiopterMax({diopter_max})"
    focus_min = focus_cfg["FocusMin"]
    focus_max = focus_cfg["FocusMax"]
    if focus_min > focus_max:
        return False, f"FocusScanConfig.FocusMin({focus_min}) > FocusScanConfig.FocusMax({focus_max})"
    motion_val = motion_item["InfinityPosition"]
    diopter_val = diopter_cfg["InfinityPosition"]
    focus_val = focus_cfg["InfinityPosition"]
    if diopter_val != motion_val:
        return False, f"DiopterScanConfig.InfinityPosition({diopter_val}) != MotionConfig({motion_val})"
    if focus_val != motion_val:
        return False, f"FocusScanConfig.InfinityPosition({focus_val}) != MotionConfig({motion_val})"

    return True, f"InfinityPosition校验通过, 值={motion_val}"


def validate_json_format(folder_name, data):
    if isinstance(data, dict) and folder_name in data:
        folder_name_data = data[folder_name]
        if isinstance(folder_name_data, list) and len(folder_name_data) == 1:
            inner_list = folder_name_data[0]
            if isinstance(inner_list, list) and len(inner_list) == 2:
                value1, value2 = inner_list
                return value1, value2
        return None, None
    else:
        return None, None


def validate_json_format_Offset(data):
    exposure_offset = data["ExposureOffset"]
    gray_offset = data["GrayOffset"]
    return exposure_offset, gray_offset


def update_status(message: str, status_callback: Optional[Callable[[str], None]] = None):
    msg = f"{message}"
    if status_callback is not None:
        try:
            status_callback(msg)
        except Exception:
            # 回调出错不中断采集，降级打印到控制台
            print(msg)
    else:
        print(msg)


def config_detection(
        eye1_path: str,
        out_path: str,
        rule_map: dict,
        out_filename: str,
        status_callback: Optional[Callable[[str], None]] = None
):
    run_time_tag = datetime_str()  # 测试开始时生成一次时间戳，保证同一次测试多组文件时间戳一致

    try:
        update_status(
            f"config detection start, time: {run_time_tag}", status_callback)
        os.makedirs(out_path, exist_ok=True)
        folder_name = get_subfolder_name(eye1_path)
        ini_path = os.path.join(eye1_path, "config.ini")
        if not os.path.exists(ini_path):
            raise RuntimeError(f"File {ini_path} no exists.")
        config = configparser.ConfigParser()
        config.read(ini_path, encoding='utf-8')
        data = gather_file_data(base_path=eye1_path, folder_names=folder_name,
                                config=config, rule_map=rule_map, status_callback=status_callback)
        base_name, ext = os.path.splitext(out_filename)
        out_file = os.path.join(out_path, f"{base_name}.xlsx")
        fill_pass = PatternFill(
            "solid", start_color="CCFFCC", end_color="CCFFCC")
        fill_loss = PatternFill(
            "solid", start_color="FFCCCC", end_color="FFCCCC")
        wb = Workbook()
        ws = wb.active
        if data:
            max_len = max(len(r) for r in data)
            headers = [f"Col_{i}" for i in range(max_len - 1)] + ["Result"]
            ws.append(headers)
            for row in data:
                ws.append(row)
                r = ws.max_row
                status = row[-1] if row else ""
                if status == "pass":
                    # pass仅最后单元格绿色
                    c = len(row)
                    cell = ws.cell(row=r, column=c)
                    cell.fill = fill_pass
                elif status == "loss":
                    # loss整行红色
                    for col in range(1, ws.max_column+1):
                        ws.cell(row=r, column=col).fill = fill_loss
        wb.save(out_file)
        wb.close()
        update_status(
            f"config detection finish, path: {out_file}", status_callback)
    except Exception as e:
        # 只要发生任何异常，都会先推送ERROR消息给UI
        err_msg = f"{type(e).__name__}: {str(e)}"
        update_status(err_msg, status_callback)
        raise
