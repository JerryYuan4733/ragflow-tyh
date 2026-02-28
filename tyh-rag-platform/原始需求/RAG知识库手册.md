# RAG知识库手册

# 知识库总览

## 原理概述-RAG 与 RAGFlow 通俗解读

![unnamed.jpeg](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/5f05258c-cfc9-4f6e-ae45-030068c11108.jpeg)

---

## 第一部分：为什么我们需要 RAG？

### 1. 通用大模型的“尴尬时刻”

你们在使用 ChatGPT 或文心一言这类通用大模型时，有没有遇到过这两种情况？

1.  **它在“一本正经地胡说八道”**（专业术语叫“幻觉”）：你问它一个很专业的问题，它编造了一个看起来很真但完全错误的答案。
    
2.  **它对咱们公司一无所知**：你问它“我们公司最新的产品定价是多少？”，它回答不了，因为那是公司内部机密，它没学过。
    

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/56ed8d5e-e6dd-444f-9eb5-534736ddfeee.png)

这就像一个博览群书的**学霸（通用大模型）**，它上知天文下知地理，但如果你突然问它你们部门上周的会议纪要，它肯定一脸懵。

### 2. 救星来了：什么是 RAG？

为了解决这个问题，聪明的工程师们发明了一种技术，叫 **RAG**（Retrieval-Augmented Generation，检索增强生成）。

别被这三个英文字母吓倒，它的原理超级简单，我们用一个比喻就懂了：

**RAG = “开卷考试”**

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/b8f3ca1f-356a-4200-af07-c58647c705c6.png)

*   **以前的模式（闭卷考试）：** 你问问题，大模型全靠脑子里的记忆回答。记错了就瞎编，没记过就不会。
    
*   **RAG 模式（开卷考试）：** 我们给大模型发了一本“参考书”（比如咱们公司的产品手册、SOP文档）。
    
    *   当有人提问时，大模型**先去翻书**，找到相关的内容。
        
    *   然后结合书里的内容，用它聪明的脑瓜子组织好语言，再回答你。
        

这样回答出来的内容，既准确（因为有依据），又通顺（因为大模型文笔好）。

---

## 第二部分：RAGFlow 是什么？它在幕后做了什么？

如果说 RAG 是“开卷考试”这个**想法**，那么 **RAGFlow** 就是实现这个想法的**全自动流水线机器**。

对于运营和业务人员来说，我们手里有大量的 PDF、Word、Excel、网页链接，这些都是乱糟糟的“原材料”。大模型是看不懂这些原始文件的。

RAGFlow 的作用，就是把这些“原材料”，加工成大模型能随时查阅的“参考书”。

### RAGFlow 的幕后工作流程（香蕉工厂版）

我们可以把 RAGFlow 想象成一个**知识加工厂**。这个过程是如何与大模型配合的呢？我们来看图：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/be9b4676-2256-407a-b53e-d5d2d1ee2d75.png)

下面我们拆解这个流程：

#### 步骤一：知识“喂养”与“切块” (Data Ingestion & Chunking)

*   **动作：** 我们把公司的产品文档、客服话术扔给 RAGFlow。
    
*   **原理：** 大模型一口气读不懂几百页的书。RAGFlow 这个机器会把长文档**切碎**成一个个小的知识点（比如一段话，一个段落）。
    

#### 步骤二：制作“智能索引” (Embedding & Indexing)

*   **这是最核心的一步！**
    
*   **原理：** 机器要怎么知道哪块“肉丁”是回答用户问题的呢？RAGFlow 会利用一种技术（向量化），给每一个知识小方块打上一个“**意义标签**”。
    
*   _比喻：_ 图书馆里的书如果不分类，根本找不到。这一步就是给每个知识点贴上极其详细的**智能标签**，并整齐地放进一个超级书架（向量数据库）里。
    

#### 步骤三：检索与生成 (Retrieval & Generation) —— 配合大模型

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/6058cd1a-4001-4ae9-968c-6043ff651cd4.png)

当业务人员在系统里提问时，奇迹发生了：

1.  **用户提问：** “我想知道 A 产品的退换货政策。”
    
2.  **超级检索（RAGFlow 的工作）：** RAGFlow 迅速理解你的问题意图，拿着放大镜去那个“超级书架”里，瞬间找出最匹配的几个知识小方块（比如找到了《退换货SOP》里的第3条和第5条）。
    
3.  **各司其职（配合大模型）：**
    
    *   RAGFlow 把找到的**几条干货**，打包发送给**大模型**。
        
    *   并对大模型说：“嘿，学霸，参考这几条内容，用人话回答刚才那个用户的问题，别自己瞎编啊！”
        
4.  **最终输出：** 大模型收到干货，发挥它的语言天赋，生成了一段完美的回答给你。
    

---

**一句话总结：RAG 就是让大模型带上我们公司的“私有知识库”去开卷考试，而 RAGFlow 就是帮我们自动整理这个知识库的高效工具。**

## 主界面总览

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/c7c76a5b-7f59-48b9-9a86-53b96531614f.png)

如果把 RAGFlow 比作一个\*\*“智能客服工厂”**，那么这个界面就是您的**“总控台”**。您将在这里完成两个最核心的工作：**“进货”**（上传知识文档）和**“验货”\*\*（测试问答效果）。

以下是主界面各板块的详细功能解读：

---

### 顶部导航栏：您的“指挥中心”

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/8e6f3b2d-034f-4bd3-a8b9-10da048a2dce.png)

这是最顶端的黑色导航区域，包含您在系统中最常用的功能入口。

*   **🏠 (首页)：** 随时点击这个小房子图标，就能回到您现在看到的这个总览界面。
    
*   **知识库 (核心功能)：** 相当于\*\*“仓库”\*\*。这是您工作最频繁的地方，所有的文档（PDF、Excel、Word）都要在这里创建分类并上传。
    
*   **聊天 (核心功能)：** 相当于\*\*“体验店”\*\*。当您传好文档后，要点击这里去和 AI 对话，测试它答得准不准。
    
*   **文件管理：** 如果您想查看上传过的所有原始文件列表，可以在这里找。
    

_(注：右侧的“搜索”、“智能体”、“记忆”属于进阶功能，初期维护知识库时暂时用不到，可以先忽略。)_

---

### 中间核心区：两大板块

界面主体分为上下两排卡片，分别对应了 AI 知识库搭建的两个阶段。

#### 🟢 上半部分：知识库 (Knowledge Base) —— “原材料仓库”

这一排展示了目前系统中已经建立的知识分类。每一个方块（卡片）代表一个独立的知识主题。

*   **例子：**
    
    *   **“终端销售”**：可能存放了销售话术、产品卖点文档。
        
    *   **“天一泓公司政策知识库”**：可能存放了员工手册、报销流程等 PDF 文件。
        
    *   **“运营部-Q&A问答对”**：这应该就是运营同事整理好的 Excel 问答表，用于精准回答。
        
*   **卡片信息含义：**
    
    *   `1个文件` / `22个文件`：显示这个库里“喂”了多少份资料。
        
    *   时间戳：显示最后一次更新资料的时间。
        
*   **你要做什么？**
    
    *   如果您有新的业务线，您需要点击右上角的 `Create` (新建) 按钮创建一个新卡片。
        
    *   如果您要更新旧资料，点击对应的卡片进去，上传新文件或删除旧文件。
        

#### 💬 下半部分：聊天 (Chat) —— “产品体验区”

这一排展示了不同的对话助手。您可以把每个卡片理解为一个配置好的\*\*“机器人客服”\*\*。

*   **截图中的例子：**
    
    *   **“设备技术咨询”**：这个机器人可能关联了技术手册的知识库，专门回答维修问题。
        
    *   **“运营知识库”**：这个机器人可能关联了上面的运营 Q&A，供内部员工查询使用。
        
*   **你要做什么？**
    
    *   **日常测试：** 每次在“知识库”里更新了文档后，**一定要**来到这里，点开对应的聊天卡片，模拟用户提问（比如问：“报销流程是什么？”），看看 AI 的回答是否符合预期。
        
    *   如果回答不对，就说明上面的“知识库”里的文档没整理好，或者解析模式选错了。
        

---

#### 总结：日常工作流

看着这个界面，您的脑海里应该有这样一条清晰的操作动线：

1.  **准备资料：** 在电脑上整理好 Word 或 Excel。
    
2.  **入库（点击上方“知识库”）：** 找到对应的卡片（例如“公司政策”），点进去上传文件，等待系统解析。
    
3.  **测试（点击下方“聊天”）：** 找到对应的聊天窗口，提问测试。
    

# 操作流程

点击某个知识库进入知识库界面

## 上传并解析

这是知识库界面：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/5a625389-5283-40fb-9742-aae8f1aa3aaf.png)

### 文件上传：把资料交给 AI

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/406a12a9-676d-4ebf-babb-5aac9116871f.png)\->>>>>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/cb0d08f2-e8f8-40dc-a786-69ebb54938a1.png)

当您点击右上角的 ➕ 新增文件 按钮时，就开始了“喂”数据的过程。

操作步骤： 点击按钮 -> 选择本地文件（Word, Excel, PDF, PPT等） -> 确认上传。

注意： 此时文件只是“躺”在服务器里，AI 还读不懂，必须经过下一步的“解析”。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/91e8924a-4462-4b2f-a85f-76f6f177879b.png)

### 解析配置(重点)：告诉 AI 怎么读

由于不同文件（如 PPT、Excel、手册）的结构完全不同，您需要为每个文件指定正确的“阅读方式”。

#### 这很重要！

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/70d2238c-c166-4c1e-baa3-4ed71adfa244.png)

大模型就像一个很聪明但“视力不好”的厨师。如果我们直接把 PPT、表格、长文本一股脑扔给他，对他来说就是一堆乱码。**因为 PPT 是一页一页的，Excel 是一行一行的，手册是一段一段的**，结构完全不同。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/cacdab29-8481-415b-bebe-dbcde5549679.png)

如果我们用同一种方式去读所有文件（比如把 Excel 当成普通作文来读），就会导致信息错乱。表格里的数据失去了表头，PPT 里的图片失去了说明。**“一刀切”的读取方式只会产生“知识垃圾”。**

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/468db460-f7a9-4538-a846-29a5ac440019.png)

我们需要给 AI 换上对应的“眼镜”：

*   **PPT 模式**：告诉 AI 每一页是一个独立的话题。
    
*   **Excel 模式**：告诉 AI 第一行是表头，每一行是一条完整的数据。
    
*   **手册模式**：告诉 AI 留意目录和层级结构。
    

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/dd5ebb67-6efe-4b9c-923c-b4af6e47459c.png)

只有“读得对”，才能“记牢靠”。有了精准的解析配置，我们的业务文档才能变成高质量的**结构化知识**。这样大模型在回答业务问题时，才能像查字典一样快、准、稳。

**（解析如何配置见下章：文档的类型和解析方法）**

**操作步骤：**

*       在文件列表中，找到刚上传的文件。
    
*       点击该文件对应的 “解析” (Parser) 列（例如图中显示的 presentation 或 table 处）。
    
*       在弹出的设置中，选择要求的解析模式（如：PPT 选 Presentation，pdf手册选 Manual）。并做好参数配置。参数如何配置？请参考下一章节的内容。
    
*   点击绿色三角后：始终勾选"应用全局自动元数据设置"：
    

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/6141e623-19f7-40f7-b979-71fb14f9fac9.png)

**状态检查：**

*       解析中：图标会转动，请耐心等待。
    
*       ✅ 绿色圆点：代表解析成功，AI 已经成功提取了知识。
    
*       ❌ 红色圆点：代表解析失败，通常是因为文件加密、损坏或格式极其复杂。
    

解析进行中：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/7e7e3667-fbaa-4a9f-84ae-57c7192d5611.png)

解析完成：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/4a23df79-2b24-4f97-92c1-3d0c60bafa9d.png)

1.  质量验收：检查 AI 读得对不对
    

解析成功后，不要急着离开，运营人员需要进行简单的\*\*“验货”\*\*。

**查看解析结果： 点击文件名称。**

    ✅ 优质表现： 您能看到文字被整齐地切成了若干个“块”（Chunks），且文字内容没有乱码，逻辑清晰。

比如：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/78fbda0c-3fbd-489a-a590-d7227847bd16.png)

    ❌ 劣质表现： 预览里全是乱码，或者一整页 PPT 的文字被挤成了一团。这时您可能需要联系技术人员调整参数，或重新整理原文档。

### 批量操作

你可以选择多个文件进行批量操作，但是注意确保每个文件的解析模式都被正确配置。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/be7ef374-2641-41fc-8146-1157a20e1a44.png)

## 对话测试

找到自己部门的聊天：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/c563ca59-c015-4212-9fac-8f768e88e07c.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/2b1ee968-e2bf-4cd4-94d3-eed2f4bf9724.png)

不用关心聊天设置，这些配置技术人员会提取配置好。

1.  左侧栏：对话历史管理
    

这里存放着您所有的测试记录。

*   新建会话 (New session)： 每次测试一个新话题时，建议开启新会话，避免旧的聊天上下文干扰 AI 的判断。
    
*   搜索历史： 当您积累了大量测试案例时，可以通过搜索框快速找到之前的对话。
    

1.  中间区：模拟用户对话（核心验货区）
    

这是模拟真实用户提问的地方。

引用来源（小图标）： 注意看 AI 回答下方的绿色图标（如 faqs记录.xlsx）或 Fig. 2 等字样。

    运营关注点： 点击这些图标，系统会直接定位到知识库中的原始片段。如果 AI 答错了，通过这个图标您就能瞬间发现是哪份文档、哪个段落写得有问题。

输入框： 模拟用户的各种“刁钻”问法，看 AI 能否接得住。

**运营人员的“验货”三部曲**

*   **首问：** 问一个文档里的标准问题，看 AI 能否直接提取到答案。
    

*   **追问：** 换一种不专业的问法（比如用大白话或方言），看 AI 能否通过“语义理解”匹配到知识。
    

*   **反查：** 点击回答下方的引用文档，确认 AI 没有“张冠李戴”。
    

# 文档类型和解析方法

**所有解析方式和对应的文档格式对照表见附录1**

## General解析方法

### 支持的文件格式和适用条件

**适用场景：** 大多数无法归类的文档，或者格式简单的纯文本说明。

此解析方法支持：MD, MDX, DOCX, XLSX, XLS (Excel 97-2003), 

PPT, PDF, TXT, JPEG, JPG, PNG, TIF, GIF, CSV, JSON, EML, HTML

但仍然只建议使用md或者docx格式的文档

### 解析逻辑

系统会像切香肠一样，按照设定的长度（Token数），机械地把文章切成一段一段。它不一定能完美识别段落结构，主要保证内容都被录入。

### 配置

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/09ee14d9-722b-461c-a817-99bcb875be0f.png)

*   **Chunk  (分块大小)：** 相当于“每一口吃多少字”。设得太大，AI 检索时会读太多无关信息；设得太小，句子可能被切断。_建议值：通常 512 或 1024。_
    

*   **Delimiter (分隔符)：** 告诉系统遇到什么符号就切一刀（比如句号、换行符）。
    

### 元数据(可选)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/d44cd78f-7693-4a1b-8d7c-e7c39b1a1d70.png)

注意：如果要添加元数据，建议要在解析文档前配置好元数据，因为元数据是在解析的过程中提取的。在文件的解析配置弹窗中，先勾选 “自动元数据” 开关。

#### 什么是元数据？（生活化类比）

想象你正在管理一个巨大的仓库，里面有几千个包裹。

*   普通搜索： 你喊一嗓子“谁家里有苹果？”，AI 要翻遍所有包裹内容。
    
*   元数据搜索： 每个包裹外面都贴了标签——水果类型：苹果、产地：山东、入库日期：2026-02-01。
    
*   作用： 定义这些标签的格式（比如必须标记“产地”），然后让 AI 这个“智能分拣员”在解析时自动填好。
    

#### 核心操作：如何配置一个“智能标签”？

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/560df5e1-f332-482e-97b7-dbfed8c180c4.png)

根据您提供的截图，运营人员在设置元数据字段时需要填写三个核心项： **A. 字段名称 (Field) —— 给标签起名**

*   怎么填： 建议使用英文或拼音（如 device\_type 或 chan\_pin），方便系统后台识别。
    
*   用途： 它是这个信息的唯一身份 ID。
    

**B. 描述 (Description) —— 告诉 AI “找什么”**

*   这是最关键的一步！ 你在用自然语言给 AI 下指令。
    
*   示例（参考截图）： “请识别这段文字中出现的设备型号是什么？”
    
*   运营技巧： 描述越具体，AI 找得越准。不要只写“型号”，要写“请从文中提取具体的设备硬件型号名称”。
    

**C. 值 (Value) 与 限制规则 —— 规范答案**

*   限制为已定义的值： 开启后，AI 只能从你给出的选项里选。
    
*   示例： 你定义了 型号1, 型号2, 型号3。如果文中出现了“老款型号4”，AI 会因为不在选项内而略过，从而保证数据的整齐。
    

1.  **为什么要费力配置元数据？**
    
    对运营来说，配置好元数据有两大核心好处：
    
    精准过滤（降噪）：
    
        如果用户问：“AX-100 型号的保修期多长？”
    
        系统会先通过元数据过滤掉所有不属于 AX-100 的文档，只在精准的范围内找答案。这能极大减少 AI “胡言乱语”的概率。
    
    结构化统计：
    
        你可以轻松看到知识库里：关于“型号1”的文档有多少份，关于“北京地区”的政策有多少条。
    
2.  **运营操作流程 (SOP)**
    

开启开关： 在文件的解析配置弹窗中，先勾选 “自动元数据” 开关。

进入设置： 

可以直接点击"设置元数据"

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/f9f24682-06fd-464d-9691-1db8f8af3bc4.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/c7d057a3-7175-4d00-9b5a-55e13c82aee8.png)

也可以：数据管道->自动元数据 设置

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/afcc5926-14ef-4f75-a828-c2577c08e8da.png)》》》》![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/6345a8c1-0ed1-446f-ad9a-bf68169837c6.png)

添加字段：

 点击 + 号，按照上面的 A/B/C 三步定义你想要的标签（如：业务分类、紧急程度、适用人群）。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/c0849583-4259-4387-ac16-1c87c21a5308.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/c81ea5b7-0b6b-435e-8376-d44544b20cf9.png)

##### 是否启用 "限制为已定义的值"？

如果启用 "限制为已定义的值"，那么就代表提取的内容只能限定在自定义的“值”当前也就是枚举类型。

比如：如果我们设置一个日期，那么不应该启用 "限制为已定义的值"，因为日期范围太大了。如果我们设置产品型号，我们可以通过启用 "限制为已定义的值"，来限制产品型号的选项有哪些，防止AI提取到一个不存在的产品型号。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/df78c0c8-0973-4b3a-bdc2-89fa4ecfdb95.png)

最后，保存解析： 保存后重新点击“解析”。AI 就会在切分文档的同时，像考卷打分一样，把每一段对应的标签填好。

### 文档规范

文档应当层次分明，有大标题，小标题等层次结构，尽量不要包含图片或者表格。如果包含图片和表格，需要在图片和表格的上下文对图片和表格做出解释，表格应当简洁。

| **✅ 优质文档 (AI 喜欢)** | **❌ 劣质文档 (AI 可能会晕)** |
| --- | --- |
| **层级分明：** 标题使用 Word 标准的“标题1、标题2”样式。 | **格式混乱：** 全文没有分段，或者用空格键来做缩进。 |
| **标点规范：** 句子结束有明确的句号。 | **缺乏标点：** 文字堆砌，甚至用截图代替文字。 |
| **内容连续：** 每一段话把一件事情讲清楚。 | **过度排版：** 为了美观把一句话拆成好几行，中间插入大量装饰性符号。 |

## Q&A解析方法

### 支持的文档格式和适用条件

**适用场景：** 客服话术库、FAQ（常见问题解答）、通过 Excel 整理好的知识点。

此块方法支持 **excel** 和 **csv/txt** 文件格式。

### 解析逻辑

系统会自动寻找“问题”和“答案”的对应关系。如果是 Excel，它通常默认第一列是问题，第二列是答案。

### 配置

没有需要手动配置的参数

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/8cc4d220-64e8-4783-819c-5197dc5be07a.png)

### 文档规范

1.  所有的Q&A问答对文档只能有两列，第一列是"问"，第二列是"答"
    
2.  如果文件是 **excel** 格式，则应由两个列组成:       **不要有标题**：一个提出问题，另一个用于答案。  一行一个问答对。不要合并单元格！
    
3.  如果文件是 csv/txt 格式       以 UTF-8 编码且用 TAB 作分开问题和答案的定界符。    
    

未能遵循上述规则的文本行将被忽略，并且 每个问答对将被认为是一个独特的部分。

| **✅ 优质文档** | **❌ 劣质文档** |
| --- | --- |
| **问题穷举：** 一个标准答案对应多个不同问法的“相似问”（可以在 Excel 中多加几列相似问）。 | **合并单元格：** Excel 中为了好看，把多个问题合并到一个大单元格里。 |
| **答案独立：** 答案列包含完整的上下文，不要写“见上文”。 | **依赖上下文：** 答案里写“如同上述操作”，但在检索时 AI 看不到“上述”。 |

举例excel格式的文件(**推荐**)：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/fb90b3a4-5c4e-44ce-a9d7-886435e01e45.png)

## 结构化数据解析 (Table/Resume)

### 支持的文件格式和适用条件

**适用场景：** 产品参数表、价格表、员工通讯录等纯数据表格。 **支持格式：** Excel, CSV。

### 解析逻辑

**解析说明：** 每一行会被作为一个完整的数据条目。

### 配置

没有额外需要配置的参数

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/a51f63cc-5962-4dd1-a814-cdc07c2ed2c7.png)

### 文档规范

*   **✅ 优质文档：** 标准的二维表格，第一行是表头（如：型号、价格、颜色）。
    

*   **❌ 劣质文档：** 复杂的嵌套表头、斜线表头、表头在侧面的表格。
    

示例：

![table-02.e4d2487c.svg](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/16210616-7f62-4702-ba39-18ebc88abccb.svg)

## 专业文档解析

这四类专门针对特定排版的 PDF/Word 进行了优化：

| **模式** | **适用场景** | **解析特点** | **文档要求 (重点)** |
| --- | --- | --- | --- |
| **Manual (手册)** | 包含大量层级标题的操作手册、说明书。 | 极度依赖标题层级来识别内容块。 | **必须有清晰的目录结构**。如果 PDF 左侧没有导航目录，解析效果会大打折扣。 |
| **Paper (论文)** | 学术论文。 | 能够识别双栏排版、摘要、参考文献。 | 必须是标准的学术论文排版（如双栏）。 |
| **Book (图书)** | 小说、长篇教材。 | 按章节切分，保留长文本的连贯性。 | 章节标题必须显著，正文段落清晰。 |
| **Laws (法律)** | 法律法规、公司制度。 | 严格保留条款编号（如“第一条”、“1.1”）。 | 严禁打乱条款序号，**条款编号必须标准**（如“第一章”而不是“一、”混用）。 |

### 配置(上面4类的配置相同)

元数据操作参考上文General的

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/7dadd984-5ca4-412b-8839-950c95af0502.png)

| **模式** | **AI 在后台偷偷干了什么** | **关注点** |
| --- | --- | --- |
| **Presentation** | 尝试把 PPT 里的图表和文本对应起来。 | 自动问题提取非常重要，因为 PPT 往往字少，需要 AI “脑补”。自动问题设置为5，关键词提取设置为2。 |
| **Picture** | 开启文字识别 (OCR)，把图里的字抠出来。 | 关键词提取很重要，能帮 AI 理解图片的核心主题。自动问题设置为2，自动关键词提取设置为15. |
| **One** | 把整份文件当成一个大块，不切碎。 | 适合短文，不需要生成太多关键词，否则会乱。自动问题设置为3，自动关键词提取设置为10. |
| **Tag** | 把它当成一份词典，不作为问答来源。 | 通常不需要自动问题提取，设置为0，自动关键词提取设置为1。 |

元数据设置：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/9eacd6c4-a53c-411b-b8ef-90ba2fa9ff29.png)

示例：

manual：

分界清晰

![manual-02.1a214f22.svg](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/567ce4a7-7d26-4f13-b2e3-e9dd6a6bd6dd.svg)

law：

![law-01.7070b7b3.svg](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/0ff74664-f566-4c6f-9697-a90f62457d7d.svg)

book：

![book-04.594d0d1a.svg](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/ab12f271-f85d-40ba-b359-f6f08336869e.svg)

paper：

![paper-01.e0019dcd.svg](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/91eb6a51-e8c1-4633-9da6-9316e564ba77.svg)

## 特殊解析 (Presentation / Picture / One / Tag)

### 演示文稿 (Presentation)

适用： PPT 文件。

说明： AI 会提取每页 PPT 的文字。

❌ 避坑： 如果 PPT 里全是截图（没有可选中的文字），AI 是读不到内容的（除非开启 OCR，但速度慢）。

### 整体模式 (One)

适用： 非常短的文件，且内容绝对不能拆分。

逻辑： 整个文件作为一个整体（一个 Chunk）。

✅ 场景： 一个只有 200 字的公司简介。

❌ 避坑： 千万别传几万字的书进去，否则超出了 AI 的单次处理上限，会直接报错或被截断。

### 标签模式 (Tag)

适用： 这不是用来回答问题的，而是给其他文件“打标签”的词库。

场景： 比如你有一堆车型的标签，用于后续检索过滤。

### 示例

tag：

![tag-01.ff996302.svg](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/a618c5f7-addd-4fa1-a8de-c376624b8ff0.svg)

one：

完整的一个文档作为一个整体。

![one-02.0adb16f8.svg](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/38ab8102-1c3f-4a18-a11c-c785e6c6dcf0.svg)

presentation：

![presentation-01.06115027.svg](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/8a0f346f-1675-49b3-823c-b83fd99d9fe8.svg)

# 文档规范

## 黄金法则

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/258f70a6-4e86-42a8-96b8-3325bc2c4fd9.png)

*   **垃圾进，垃圾出 (Garbage In, Garbage Out)：** 哪怕 RAGFlow 再强大，如果文档里充满了错别字、乱码、或者逻辑不通的句子，AI 绝对回答不好。
    

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/389566ec-9dde-498a-a87e-59e99bf7b617.png)

*   **Excel 是永远的神：** 如果你有精力整理，**Q&A 模式 + Excel** 是目前让 AI 回答最准确的方式。把用户常问的问题整理在 A 列，标准话术放在 B 列。
    
*   ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/7b9f8fa3-1b7c-4f9d-acc6-3e5eb9139653.png)
    

*   **PDF 避坑：** 尽量不要上传“图片转 PDF”的文件（即文字无法选中的 PDF）。如果必须传，请确保文字清晰端正。
    

*   **段落独立性：** 想象你在写一个个独立的知识卡片。每一段话（或每一个分块）最好能独立读懂，不要过度依赖“见上一页”。
    

## 格式与排版规范

AI 喜欢结构清晰的纯文本，不喜欢复杂的视觉设计。

### 推荐的文件格式

提供Q&A问答对最好，但如果没办法提供Q&A问答对，那么：

*   **首选：** `.md` (Markdown), `.txt`, `.docx` (Word 文档)。
    
*   **次选：** `.pdf` (必须是文字版，**严禁使用**扫描版/图片版 PDF)。
    
*   **避免：** `.pptx` (PPT 内容如果不转成大段文字，AI 很难理解上下文)，`.xlsx` (除非是简单的二维表，否则不要用 Excel 存文本)。
    

### 标题层级要严格

AI 依靠标题来理解段落的主题。

*   **使用标准层级：** 必须使用 Word 或 Markdown 的标准标题功能（H1, H2, H3）。
    
*   **不要用字号代替标题：** 不要只是把字加粗放大当标题，要在软件里选择“标题1”、“标题2”。
    

### 表格与图片的特殊处理

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/a467a9dc-7362-416d-8fce-a2efb9e0f0ef.png)

*   **图片：** AI **看不到**文档里的图片内容。如果是流程图或截图，**必须**在图片下方用文字详细描述图片里的信息。
    
*   **表格：**
    
    *   **能不用就不用：** 尽量转化为文字列表。
        
    *   **如果必须用：** 严禁使用“合并单元格”或复杂的嵌套表。必须是简单的“行-列”对应关系。
        

## 内容写作规范

这是最重要的一点。AI 会把文章切成小块，我们需要保证**每一块切下来都能独立读懂**。

### 原则一：上下文独立 (Contextual Independence)

避免使用“它”、“上述”、“如下图所示”等指代词，因为 AI 切片时可能切不到上一段，导致它不知道“它”是谁。

*   **❌ 错误写法：**
    
    > 产品具有防水功能。**它**符合 IP68 标准，**该标准**意味着可以在水下工作。 _(如果 AI 只切到了后半句，它不知道“它”是指产品，也不知道 IP68 是指防水。)_
    
*   **✅ 正确写法：**
    

> Model-X 智能手表具有防水功能。Model-X 符合 IP68 防水标准，IP68 标准意味着 Model-X 可以在 1.5米深的水下工作 30 分钟。 _(哪怕只把这一句拿出来，谁都能读懂。)_

### 原则二：段落短小精悍

不要写长篇大论不换行。

*   **建议：** 每个段落最好只讲**一个**具体的知识点。
    
*   **长度：** 单个段落建议控制在 200-500 字之间。如果太长，请拆分成小标题或列表。
    

### 原则三：关键词显性化

用户提问时会用很多不同的词，文档里要尽量覆盖这些词。

*   **建议：** 在文档开头或结尾，增加一个 `【相关关键词】` 模块，罗列该文档涉及的专有名词、别名、俗称。
    
    *   _例如：_ 官方名称是“人力资源管理系统”，关键词里可以加上“HR系统”、“EHR”、“考勤系统”。
        

## 最佳实践结构：QA 问答对

对于常见问题（FAQ）或操作手册，**最适合 RAG 的格式是“问答对”**。这种格式检索匹配度最高。

### ✅ 推荐格式 (Q&A)

如果您正在整理 FAQ，请直接遵循以下格式：

> **Q: \[用户可能会问的问题\]A:** \[直接、准确的答案，包含所有必要条件\]

**示例：**

> **Q: 如何申请公司的加班餐补？A:** 申请公司加班餐补需要满足两个条件：1. 加班时间超过晚上 20:00；2. 在钉钉系统中提交“加班申请”。满足条件后，请在钉钉“报销流程”中上传餐饮发票，报销额度上限为 50 元/次。

### ❌ 避免的格式 (多轮对话式)

不要把文档写成剧本或聊天记录，AI 很难从中提取确切的规则。

## 自检

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/1ccf16f0-546d-443a-b8f0-bf684fbc2d09.png)

在将文档上传到知识库之前，请对照检查：

```plaintext
[ ] 文件格式： 是 Word 或 Markdown 吗？（不是扫描件）

[ ] 标题清晰： 使用了 H1/H2 等标准标题样式吗？

[ ] 拒绝指代： 是否把“它/这个/上述”替换成了具体的名词？

[ ] 信息补全： 图片里的信息是否都用文字写出来了？

[ ] 单点单义： 每一个段落是否只讲清楚了一件事？

```

# 评分标准

评分是衡量"信赖"的关键

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/a5820963-e7b7-4082-862a-fee3c5061fff.png)

机器人虽然看起来很专业，但业务员心里在打鼓：“它说得头头是道，但万一给客户说错了，这锅谁背？”

AI 最大的问题是它永远看起来很自信，哪怕是在胡说八道。在正式把 AI 推给客户或投入业务之前，我们必须给它安排一场\*\*“上岗考试”\*\*。如果不测试，我们就不知道它是一个“真专家”还是一个“大忽悠”。

---

### 第一步：构建“黄金标准”测试集 (Golden Dataset)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/afd61d59-a0e3-484b-9b8e-53c9d2ad48f9.png)

要考 AI，我们得先有标准。业务人员要挑选出最核心、最常被问到的 10-20 个问题，并**亲手写下“标准答案”**。这就是我们的“黄金标准测试集”。没有这个标尺，我们就无法衡量 AI 到底做得好不好。

验证前，业务人员必须先准备好“参考答案”。

*   **出题：** 从知识库中挑选出 10-20 个核心业务问题（涵盖常见故障、政策细节、操作步骤）。
    
*   **定标：** 手动写出这些问题的“标准答案”。
    

### 第二步：执行“盲测”与评分

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/bef177f4-2008-45e4-9ed8-3f3625706bee.png)

我们像考官一样盯着它的表现，主要看两点：

1.  **它翻对书了吗？**（检索命中率）：如果它回答退货政策，却引用了食堂菜单，那就是“找错书了”。
    
2.  **它说对话了吗？**（回答准确率）：看它是否逻辑清晰。是满分通过，还是部分正确，或者是完全在“幻觉”瞎编。
    

#### 实际操作：

将测试集中的问题输入到 RAGFlow 的“聊天”窗口中，由业务人员对 AI 的表现进行打分。建议从以下三个维度观察：

#### 1. 检索命中率（Retrieval Accuracy）—— 考点：有没有找对资料？

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/1d9335a0-6783-47d8-af9b-6ce89e1a964a.png)

*   **验证方法：** 观察回答下方的**引用来源图标**（如 `faqs记录.xlsx`、`Fig. 2` 等）。
    
*   **60% 标准：** 如果 10 个问题中，有 6 个问题引用的确实是包含答案的那份文件或图片，则检索合格。
    

#### 2. 回答准确率（Generation Accuracy）—— 考点：有没有胡言乱语？

*   **验证方法：** 对比 AI 给出的文字描述与业务专家写的“标准答案”。
    
*   **评分细则（建议）：**
    
    *   **3分（完全正确）：** 逻辑清晰，核心数据、步骤无误。
        
    *   **2分（部分正确）：** 找到了核心答案，但丢了一些次要细节。
        
    *   **1分（含糊）：** 回答了相关内容，但没直接解决问题。
        
    *   **0分（幻觉/错误）：** 编造事实或答非所问。
        

### 第三步：计算总分

通过公式计算出的准确率百分比，就是 AI 的\*\*“信用分”\*\*。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/ABmOoWbVVAWPVOaw/img/a0b53399-2ce1-494e-8f9b-9d861c5ca6af.png)

业务部门可以采用以下公式进行量化：

$\text{准确率} = \frac{\sum \text{实际得分}}{\text{总题数} \times \text{最高分(3分)}} \times 100\%$

> **示例：** 50 道题，总分 150 分。如果 AI 最终得分 90 分，准确率为 60%，即通过验收。

---

# FAQ

### 📋 第一部分：新手上路与基础概念

**Q1：RAGFlow 到底是干什么用的？我每天主要在上面做什么？A：** 您可以把 RAGFlow 想象成一个“智能客服工厂”。您每天主要做两件事：

**“进货”**（在**知识库**界面）：上传公司政策、产品手册、话术表，让 AI 学习 。

**“验货”**（在**聊天**界面）：假装成客户向 AI 提问，检查它答得准不准 。

**Q2：我能上传哪些格式的文件？**

**A：** 系统支持 Word (.docx)、Excel (.xlsx)、PPT (.pptx)、PDF、TXT 以及 Markdown (.md) 等常用格式 。

**特别推荐：** 整理好的 Excel 问答对、Word 文档、Markdown 文档 。

**尽量避免：** 扫描版的 PDF（全是图片没法选字的那种）或者纯图片的 PPT，除非您不仅为了存文档，还开启了耗时的 OCR 功能 。

**Q3：上传文件后，文件名旁边的小圆点是什么意思？A：** 这是文件的“解析状态”：

**🟢 绿色圆点：** 成功！AI 已经读懂了内容，可以去聊天界面测试了 。

**🔴 红色圆点：** 失败。可能是文件加密了、损坏了，或者格式太复杂 AI 读不出来，建议检查文件后重试 。

---

### 📄 第二部分：文档准备（避坑指南）

**Q4：为什么我传了文档，AI 回答还是一塌糊涂（胡言乱语）？**

**A：** 记住黄金法则：**“垃圾进，垃圾出”** 。请检查您的文档是否存在以下问题：

**错别字多、逻辑不通** 。

**排版混乱**：没有用标准的“标题1、标题2”层级，全文是大段不换行的文字 。

**依赖上下文**：段落里大量使用“如上所述”、“如下图”这种词。AI 切片后可能看不到“上面”是什么。每一段话最好能独立读懂 。

**Q5：我要整理客服常见问题（FAQ），用什么格式最好？**

**A：** **Excel 是永远的神！** 。

**格式要求：** 第一列写“问题”，第二列写“答案” 。

**严禁：** 合并单元格！一行只能有一个问答对 。

**技巧：** 如果一个问题有多种问法（比如“价格多少”和“多少钱”），可以在 Excel 中多加几列写相似问 。

**Q6：如果是产品手册或操作说明书，要注意什么？A：**

*   如果是 Word/PDF，必须有清晰的**目录结构**（标题层级），AI 极度依赖标题来识别内容块 。
    
*   不要把文字做在图片里！AI 看不到图片内容。如果有流程图，请在图片下方用文字把流程描述一遍 。
    

---

### ⚙️ 第三部分：解析与配置（进阶操作）

**Q7：上传文件时，“解析模式”怎么选？A：** 根据文件类型对号入座：

**Excel 问答表：** 选 **Q&A** 模式 。

**产品参数表/价格表：** 选 **Table** 模式 。

**操作手册/说明书（PDF）：** 选 **Manual** 模式 。

**PPT 演示文稿：** 选 **Presentation** 模式 。

**实在不知道选什么：** 选 **General**（通用模式） 。

**Q8：配置里的“Token (分块大小)”和“Chunk”是什么意思？A：** 想象 AI 吃东西。

*   **Chunk (分块)：** 就是 AI 一口吃进去的内容块。
    
*   **Token (分块大小)：** 就是这一口有多大。
    
*   **设太大：** AI 一次读太多无关信息，容易晕。
    
*   **设太小：** 句子被切断了，意思不连贯。
    

**建议值：** 通常保持默认的 **512 或 1024** 即可 。

**Q9：什么是“元数据 (Metadata)”？我为什么要配置它？**

**A：** 元数据就是给文档贴的\*\*“智能标签”\*\*（比如：`适用地区: 巴西`，`产品型号: AX-100`） 。

**好处：** 当用户问“AX-100 的保修期”时，AI 会先过滤掉所有不属于 AX-100 的文档。这样能极大减少 AI 答非所问的情况 。

**操作：** 您需要在解析设置里定义字段（Field）和描述（Description），告诉 AI 怎么去提取这些标签 。

---

### ✅ 第四部分：测试与验收

**Q10：怎么才算“测试通过”？有没有量化标准？**

**A：** 建议进行“盲测”。准备 10-20 个真实业务问题和标准答案，对比 AI 的回答 。

**及格线：** 检索命中率（找对文件）和回答准确率（说对话）达到 **80%** 以上 。

**评分公式：** (实际得分 / 总分) × 100% 。

**Q11：AI 回答错了，我怎么知道它是看了哪份错误的文档？**

**A：** 在聊天界面，看 AI 回答下方的**绿色小图标**（引用来源） 。

*   点击图标，系统会直接跳转到原始文档的对应段落。如果发现那段话写错了，或者 AI 找错了段落，您就可以针对性地去修改文档或调整元数据 。
    

# 附录

## 解析方式-文档格式支持  对照表

| **模板名称** | **描述** | **支持的文件格式** |
| --- | --- | --- |
| **通用 (General)** | 文件根据预设的分块 Token 数量进行连续分块。 | MD, MDX, DOCX, XLSX, XLS, PPT, PDF, TXT, JPEG, JPG, PNG, TIF, GIF, CSV, JSON, EML, HTML |
| **问答 (Q&A)** | 提取相关信息并生成问答对，用于回答问题。 | XLSX, XLS, CSV/TXT |
| **简历 (Resume)** | 简历格式的文件。 | DOCX, PDF, TXT |
| **手册 (Manual)** | 适用于技术手册解析。 | PDF |
| **表格 (Table)** | 使用 TSI 技术进行高效的表格数据解析。 | XLSX, XLS, CSV/TXT |
| **论文 (Paper)** | 针对学术论文排版进行优化。 | PDF |
| **图书 (Book)** | 适用于长文本书籍解析。 | DOCX, PDF, TXT |
| **法律 (Laws)** | 针对法律条文、法规文件进行优化。 | DOCX, PDF, TXT |
| **演示文稿 (Presentation)** | 针对幻灯片内容进行解析。 | PDF, PPTX |
| **图片 (Picture)** | 纯图片解析。 | JPEG, JPG, PNG, TIF, GIF |
| **整体 (One)** | 每个文档被视为一个完整的块进行分块（不切分）。 | DOCX, XLSX, XLS, PDF, TXT |
| **标签 (Tag)** | 该数据集作为其他数据集的标签集使用。 | XLSX, CSV/TXT |