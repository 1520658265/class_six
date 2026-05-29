角色资产归档规则

1. AI 原图保留
- 后续 AI 生成图片只做分类归档和命名整理。
- 除非用户单独要求，不做切图、缩放、转 PNG、抠透明、压缩或任何会改变图片本身的处理。
- 原图优先放入对应角色目录的 raw/ 子目录。

2. 命名
- Prompt 文件继续使用中文名，方便和剧情/资产清单对应。
- 工程归档图片使用英文资产 ID，避免 Godot 导入和跨平台路径问题。

3. 战斗帧
- 主角后续战斗帧必须适配现有 weapons/ 里的可替换武器。
- 角色本体不要画死武器，需保留 WeaponSlot/手部挂点。

4. 本批核心 NPC 原图
- baoxianjin/raw/char_baoxianjin_concept_v2.jpg
- baosimu/raw/char_baosimu_concept_v1.jpg
- zengjianming/raw/char_zengjianming_concept_v1.jpg
- wangyan/raw/char_wangyan_concept_v1.jpg
- caozhengdong/raw/char_caozhengdong_concept_v1.jpg

5. 家庭线与校园配角原图
- jiejie/raw/char_jiejie_concept_v1.jpg
- fuqin/raw/char_fuqin_concept_v1.jpg
- muqin/raw/char_muqin_concept_v1.jpg
- menwei_daye/raw/char_menwei_daye_concept_v1.jpg
- lijing/raw/char_lijing_concept_v1.jpg

6. 次要 NPC 原图
- huxiaodong/raw/char_huxiaodong_concept_v1.jpg
- zhanglei/raw/char_zhanglei_concept_v1.jpg
- caozhengdong_nainai/raw/char_caozhengdong_nainai_concept_v1.jpg
- zengjianming_baba/raw/char_zengjianming_baba_concept_v1.jpg
- zengjianming_mama/raw/char_zengjianming_mama_concept_v1.jpg

7. 核心 NPC 行走表原图
- caozhengdong/raw/char_caozhengdong_walksheet_v2.jpg
  当前可用样板：1024x1024，严格 4x4，方向基本正确。
- baosimu/raw/char_baosimu_walksheet_v2.jpg
  当前可用：1024x1024，严格 4x4，角色一致性较好。
- wangyan/raw/char_wangyan_walksheet_v3.jpg
  当前可用：1024x1024，严格 4x4；v3 去掉悠悠球后方向更稳定。
- baoxianjin/raw/char_baoxianjin_walksheet_v2_reference.jpg
  参考稿：1024x1024，严格 4x4，但个别格子方向/姿态不够稳定。
- zengjianming/raw/char_zengjianming_walksheet_v2_reference.jpg
  参考稿：1024x1024，严格 4x4，但个别格子方向不够稳定。

8. 家庭线/校园配角行走表原图
- jiejie/raw/char_jiejie_walksheet_v1.jpg
  当前可用：1024x1024，严格 4x4，方向基本正确。
- fuqin/raw/char_fuqin_walksheet_v1.jpg
  当前可用：1024x1024，严格 4x4，背篓逻辑稳定。
- menwei_daye/raw/char_menwei_daye_walksheet_v1.jpg
  当前可用：1024x1024，严格 4x4，老年体态辨识度较好。
- muqin/raw/char_muqin_walksheet_v1_reference.jpg
  参考稿：1024x1024，严格 4x4，但个别格子朝向混入正面。
- lijing/raw/char_lijing_walksheet_v1_reference.png
  参考稿：2048x2048，严格 4x4，但局部头身比例偏大，作为参考保留。

9. 次要 NPC 行走表原图
- huxiaodong/raw/char_huxiaodong_walksheet_v1.jpg
  当前可用：1024x1024，低变量策略后稳定性较好。
- zhanglei/raw/char_zhanglei_walksheet_v1_reference.jpg
  参考稿：方向仍有混入，不当作当前版本。
- caozhengdong_nainai/raw/char_caozhengdong_nainai_walksheet_v1_reference.png
  参考稿：2048x2048，老人形象好，但版面放大且可视区不够标准。
- zengjianming_mama/raw/char_zengjianming_mama_walksheet_v1_reference.png
  参考稿：2048x2048，形象对，但整体更像放大型参考表。
- zengjianming_baba/raw/char_zengjianming_baba_walksheet_v1_reference.jpg
  参考稿：版式混排，不是标准 4x4 行走表。
