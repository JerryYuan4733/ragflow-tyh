/**
 * 使用帮助 - 独立页面（含功能截图）
 */
import { useNavigate } from 'react-router-dom';

const sections = [
    {
        id: 'chat',
        icon: '💬',
        title: '智能对话',
        color: 'rgba(99,102,241,0.08)',
        border: 'rgba(99,102,241,0.2)',
        description: 'AI 知识库的核心功能。在输入框中输入您的问题，系统将自动从知识库中检索相关内容，并生成智能回答。',
        features: [
            '在底部输入框输入问题，按 Enter 发送消息',
            '按 Shift+Enter 可以换行输入多行内容',
            '点击 🎤 麦克风图标可语音输入（需 Chrome 浏览器）',
            '点击 📷 相机图标可上传图片附件',
            '首页推荐问题可直接点击快速提问',
            'AI 回答支持 Markdown 格式，包括表格、代码块等',
        ],
        image: '/help/chat_overview.png',
        imageCaption: '智能对话主界面 - 左侧会话列表，右侧对话区域',
    },
    {
        id: 'conversation',
        icon: '🛠️',
        title: '消息互动',
        color: 'rgba(16,185,129,0.06)',
        border: 'rgba(16,185,129,0.2)',
        description: '每条 AI 回答下方都有丰富的互动操作按钮，帮助您更好地使用和管理对话内容。',
        features: [
            '👍 有用 - 对回答点赞，帮助系统学习优质回答',
            '👎 无用 - 对回答点踩，系统会自动生成改进工单',
            '⭐ 收藏 - 收藏有价值的回答，可在"我的收藏"中快速查看',
            '📋 复制 - 一键复制 AI 回答内容到剪贴板',
            '🔗 分享 - 分享回答内容给其他同事',
            '🙋 转人工 - AI 无法解决时，一键生成工单转人工客服处理',
        ],
        image: '/help/chat_conversation.png',
        imageCaption: '对话详情 - AI 回答下方的互动操作按钮',
    },
    {
        id: 'session',
        icon: '📋',
        title: '对话管理',
        color: 'rgba(251,191,36,0.06)',
        border: 'rgba(251,191,36,0.25)',
        description: '通过左侧面板管理您的对话记录，支持新建、切换、搜索和删除会话。',
        features: [
            '点击 "+ 新建会话" 按钮开始一个全新的对话',
            '点击左侧会话列表中的任意会话可快速切换',
            '鼠标悬浮在会话上，点击 ✕ 按钮可删除该会话',
            '顶部搜索框可按会话标题快速筛选',
        ],
        image: '/help/chat_overview.png',
        imageCaption: '左侧面板 - 会话列表和管理功能',
    },
    {
        id: 'search',
        icon: '🔍',
        title: '搜索历史',
        color: 'rgba(59,130,246,0.06)',
        border: 'rgba(59,130,246,0.2)',
        description: '全局搜索所有历史对话消息，快速找到之前的对话内容。支持关键词高亮和一键跳转原始对话。',
        features: [
            '点击侧边栏底部 "🔍 搜索历史" 打开搜索弹窗',
            '输入关键词后点击搜索或按 Enter 键执行搜索',
            '搜索结果会高亮显示匹配的关键词',
            '每条结果显示角色标签（用户/AI）和时间',
            '点击任意搜索结果可直接跳转到原始对话',
        ],
        image: '/help/search_history.png',
        imageCaption: '搜索历史 - 关键词高亮和结果列表',
    },
    {
        id: 'favorites',
        icon: '⭐',
        title: '我的收藏',
        color: 'rgba(245,158,11,0.06)',
        border: 'rgba(245,158,11,0.2)',
        description: '收藏有价值的 AI 回答，方便日后快速查阅。支持内容预览和一键跳转到原始对话。',
        features: [
            '在对话中点击 ⭐ 收藏按钮即可收藏消息',
            '点击侧边栏底部 "⭐ 我的收藏" 查看所有收藏',
            '收藏列表显示消息内容预览和角色标签',
            '点击收藏项可直接跳转到原始对话上下文',
            '点击 "✕ 取消收藏" 可移除不需要的收藏',
        ],
        image: '/help/favorites.png',
        imageCaption: '我的收藏 - 消息内容预览和快速导航',
    },
    {
        id: 'feedback',
        icon: '💡',
        title: '意见反馈',
        color: 'rgba(139,92,246,0.06)',
        border: 'rgba(139,92,246,0.2)',
        description: '提交您对系统的使用建议和问题报告，帮助我们持续改进产品体验。',
        features: [
            '点击侧边栏底部 "💡 意见反馈" 打开反馈表单',
            '选择反馈类型：功能建议、问题报告、体验反馈 等',
            '为系统打分（1-5星），帮助我们了解整体满意度',
            '填写详细的反馈内容，描述您的需求或遇到的问题',
        ],
        image: '/help/feedback.png',
        imageCaption: '意见反馈 - 分类提交反馈和评分',
    },
    {
        id: 'docs',
        icon: '📁',
        title: '文档管理',
        color: 'rgba(239,68,68,0.05)',
        border: 'rgba(239,68,68,0.15)',
        badge: '管理员',
        description: '管理知识库中的文档资料。上传的文档将自动解析并建立索引，供 AI 对话时检索使用。',
        features: [
            '上传各类文档（PDF、Word、Excel、TXT 等）到知识库',
            '支持批量上传和管理多个文档',
            '查看文档解析状态和处理进度',
            '删除过时文档，保持知识库内容准确',
        ],
        image: '/help/docs.png',
        imageCaption: '文档管理页面 - 上传和管理知识库文档',
    },
    {
        id: 'qa',
        icon: '❓',
        title: 'Q&A 管理',
        color: 'rgba(239,68,68,0.05)',
        border: 'rgba(239,68,68,0.15)',
        badge: '管理员',
        description: '创建和维护问答对（Q&A），直接为特定问题设置标准答案，提升回答准确率。',
        features: [
            '添加常见问题及其标准答案',
            '编辑和更新已有的 Q&A 内容',
            '批量导入问答对',
            'Q&A 匹配优先于知识库检索，确保关键问题有准确回答',
        ],
        image: '/help/qa.png',
        imageCaption: 'Q&A 管理页面 - 创建和编辑问答对',
    },
    {
        id: 'tickets',
        icon: '🎫',
        title: '工单管理',
        color: 'rgba(239,68,68,0.05)',
        border: 'rgba(239,68,68,0.15)',
        badge: '管理员',
        description: '查看和处理用户反馈生成的工单。用户点踩或转人工时会自动创建工单，需要管理员跟进处理。',
        features: [
            '查看所有待处理、处理中、已解决的工单',
            '认领工单 - 将工单分配给自己处理',
            '标记工单状态：处理中 → 已解决 → 已验证',
            '工单来源追踪：自动创建（点踩）/ 手动创建（转人工）',
        ],
        image: '/help/tickets.png',
        imageCaption: '工单管理页面 - 查看和处理用户反馈工单',
    },
    {
        id: 'stats',
        icon: '📊',
        title: '统计分析',
        color: 'rgba(239,68,68,0.05)',
        border: 'rgba(239,68,68,0.15)',
        badge: '管理员',
        description: '查看系统使用数据和运营指标，了解知识库的使用情况和服务质量。',
        features: [
            '查看对话数量、用户活跃度等核心指标',
            '分析热门问题和高频关键词',
            '查看质量评分趋势和用户满意度',
            '导出统计报表用于运营分析',
        ],
        image: '/help/stats.png',
        imageCaption: '统计分析页面 - 系统运营数据看板',
    },
    {
        id: 'settings',
        icon: '⚙️',
        title: '系统设置',
        color: 'rgba(239,68,68,0.05)',
        border: 'rgba(239,68,68,0.15)',
        badge: '管理员',
        description: '配置系统参数和连接设置，包括用户管理、知识库配置、RAGFlow 连接等。',
        features: [
            '管理系统用户和权限分配',
            '配置 RAGFlow 知识库连接参数',
            '调整对话模型和检索参数',
            '系统维护和数据管理',
        ],
        image: '/help/settings.png',
        imageCaption: '系统设置页面 - 参数配置和连接管理',
    },
];

const systemFeatures = [
    { icon: '🌙', title: '深色/浅色模式', desc: '点击顶部右侧的 🌙/☀️ 图标，可在深色和浅色主题之间切换' },
    { icon: '🧪', title: '测试模式', desc: '管理员可点击顶部 "🧪 测试/正式" 切换模式，测试模式下的操作不会影响正式数据' },
    { icon: '📢', title: '系统公告', desc: '顶部公告栏会展示最新的系统通知和维护信息' },
    { icon: '👤', title: '个人中心', desc: '点击右上角头像可查看角色信息和退出登录' },
];

export default function HelpPage() {
    const navigate = useNavigate();

    return (
        <div style={{
            flex: 1, overflowY: 'auto', background: 'var(--bg)',
            padding: '0 20px 60px',
        }}>
            <div style={{ maxWidth: 900, margin: '0 auto' }}>

                {/* Header */}
                <div style={{
                    textAlign: 'center', padding: '40px 0 30px',
                    borderBottom: '1px solid var(--border)', marginBottom: 40,
                }}>
                    <div style={{ fontSize: 40, marginBottom: 12 }}>📖</div>
                    <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text)', margin: '0 0 10px' }}>
                        使用帮助
                    </h1>
                    <p style={{ fontSize: 15, color: 'var(--text3)', maxWidth: 500, margin: '0 auto', lineHeight: 1.6 }}>
                        欢迎使用 AI 知识库系统！以下是各项功能的详细说明和操作指南。
                    </p>
                    <button
                        className="btn btn-primary"
                        style={{ marginTop: 20, padding: '10px 24px' }}
                        onClick={() => navigate('/chat')}
                    >
                        ← 返回对话
                    </button>
                </div>

                {/* Quick Nav */}
                <div style={{
                    display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 40,
                    padding: '16px 20px', background: 'var(--card)', borderRadius: 12,
                    border: '1px solid var(--border)',
                }}>
                    <span style={{ fontSize: 13, color: 'var(--text3)', lineHeight: '32px', marginRight: 4 }}>快速跳转：</span>
                    {sections.map(s => (
                        <a
                            key={s.id}
                            href={`#${s.id}`}
                            style={{
                                fontSize: 13, padding: '4px 12px', borderRadius: 6,
                                background: s.color, color: 'var(--text2)',
                                textDecoration: 'none', border: `1px solid ${s.border}`,
                                transition: 'transform 0.15s',
                            }}
                            onMouseEnter={e => (e.currentTarget.style.transform = 'translateY(-1px)')}
                            onMouseLeave={e => (e.currentTarget.style.transform = 'none')}
                        >
                            {s.icon} {s.title}
                        </a>
                    ))}
                </div>

                {/* Feature Sections */}
                {sections.map(section => (
                    <div
                        key={section.id}
                        id={section.id}
                        style={{ marginBottom: 48, scrollMarginTop: 20 }}
                    >
                        {/* Section Title */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                            <span style={{ fontSize: 28 }}>{section.icon}</span>
                            <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', margin: 0 }}>
                                {section.title}
                            </h2>
                            {section.badge && (
                                <span style={{
                                    fontSize: 11, padding: '3px 10px', borderRadius: 4,
                                    background: 'rgba(239,68,68,0.12)', color: '#ef4444',
                                    fontWeight: 600,
                                }}>{section.badge}</span>
                            )}
                        </div>

                        {/* Content Card */}
                        <div style={{
                            background: section.color, borderRadius: 14,
                            border: `1px solid ${section.border}`,
                            overflow: 'hidden',
                        }}>
                            {/* Description */}
                            <div style={{ padding: '20px 24px 16px' }}>
                                <p style={{
                                    fontSize: 14.5, color: 'var(--text2)', lineHeight: 1.7,
                                    margin: '0 0 16px',
                                }}>
                                    {section.description}
                                </p>

                                {/* Feature List */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    {section.features.map((f, i) => (
                                        <div key={i} style={{
                                            display: 'flex', alignItems: 'flex-start', gap: 8,
                                            fontSize: 13.5, color: 'var(--text2)', lineHeight: 1.6,
                                        }}>
                                            <span style={{
                                                display: 'inline-block', width: 20, height: 20,
                                                borderRadius: '50%', background: section.border,
                                                color: '#fff', fontSize: 11, lineHeight: '20px',
                                                textAlign: 'center', flexShrink: 0, marginTop: 1,
                                                fontWeight: 700,
                                            }}>{i + 1}</span>
                                            <span>{f}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Screenshot */}
                            <div style={{ padding: '0 24px 20px' }}>
                                <div style={{
                                    borderRadius: 10, overflow: 'hidden',
                                    border: '1px solid var(--border)',
                                    boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
                                }}>
                                    <img
                                        src={section.image}
                                        alt={section.imageCaption}
                                        style={{ width: '100%', display: 'block' }}
                                        loading="lazy"
                                    />
                                </div>
                                <p style={{
                                    fontSize: 12, color: 'var(--text3)', textAlign: 'center',
                                    marginTop: 8, fontStyle: 'italic',
                                }}>
                                    ▲ {section.imageCaption}
                                </p>
                            </div>
                        </div>
                    </div>
                ))}

                {/* System Features */}
                <div id="system" style={{ marginBottom: 48 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                        <span style={{ fontSize: 28 }}>🌐</span>
                        <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', margin: 0 }}>
                            系统功能
                        </h2>
                    </div>
                    <div style={{
                        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                        gap: 14,
                    }}>
                        {systemFeatures.map((f, i) => (
                            <div key={i} style={{
                                background: 'rgba(139,92,246,0.05)',
                                border: '1px solid rgba(139,92,246,0.15)',
                                borderRadius: 12, padding: '16px 18px',
                            }}>
                                <div style={{ fontSize: 24, marginBottom: 8 }}>{f.icon}</div>
                                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', marginBottom: 6 }}>
                                    {f.title}
                                </div>
                                <div style={{ fontSize: 13, color: 'var(--text3)', lineHeight: 1.5 }}>
                                    {f.desc}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Footer */}
                <div style={{
                    textAlign: 'center', padding: '30px 0',
                    borderTop: '1px solid var(--border)',
                    color: 'var(--text3)', fontSize: 13,
                }}>
                    <p>如有其他问题或建议，请通过 "💡 意见反馈" 功能告诉我们！</p>
                    <button
                        className="btn btn-primary"
                        style={{ marginTop: 12, padding: '10px 24px' }}
                        onClick={() => navigate('/chat')}
                    >
                        ← 返回对话
                    </button>
                </div>
            </div>
        </div>
    );
}
