'''
版本配置文件
'''
__version__ = '0.1.2.2'
__build_data__ = "2026-05-29"
__release_notes__ = """
版本1.1.6更新内容：
1、对GUI的输入控件添加验证和默认值
2、单色定标界面添加新功能：灰度计算可选FFC均匀后的图像
3、颜色滤光片添加YA滤光片选择
4、新增工具脚本：批量生成FFC图像和计算均值图像，判断文件夹下的图像是否有效，生成ColorShift.json文件
版本1.1.7更新内容：
1、单色定标添加config.ini配置读取，读取Luminance和Radiance的Folder_Rule，写入json的文件夹命令按照这个规则
2、新增工具脚本：定标后的EYE1下的配置读取以及FFC图像有效性判断，保存结果为Excel表
版本1.1.8更新内容：
1、单色定标功能将设置自动曝光相关参数放到界面，并设为可选项；
2、SDK版本为最新的2.2.0.6版本，更新场曲自动过焦接口
版本1.2.0更新内容：
1、场曲脚本文件处理部分更新
2、GUI程序图标添加
3、区分不同python版本的GUI程序
update(0.1.2.1):
1、dark heatmap capture  (height, width = img.shape) modify to (height, width = img.shape[:2])
update(0.1.2.2):
1、update dark heatmap UI log style
2、update capture_dark_heatmap.py
update(0.1.3.3):
1、field_curve\fourcolor_calibration\dark_heatmap\mono_calibration\sph_cyl_coefficient更新
2、更新内容：运行日志输出格式更新；界面控件微调；脚本更新，添加main函数，可单独应用。
"""
