"""Command-line interface for CrawlFeasibility"""
import argparse
import asyncio
import json
import logging
import sys
import io
from pathlib import Path
from typing import Optional, List

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

import config
import yaml
import json
from src import __version__
from src.crawler import BasicChecker, TechStackChecker, AntiSpiderChecker, Assessor
from src.models.result import BasicResult, TechStackResult, AntiSpiderResult, AssessmentResult, CrawlFeasibilityResult
from src.utils.http_client import HttpClient
from src.utils.cache import cache_manager

logger = logging.getLogger(__name__)
console = Console()


class CrawlFeasibilityCLI:
    """CLI for CrawlFeasibility"""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.client: Optional[HttpClient] = None

    async def run(self):
        """Main execution flow"""
        if self.args.version:
            print(f"CrawlFeasibility v{__version__}")
            return

        # Handle batch mode
        if self.args.batch:
            await self._run_batch()
            return

        # Single URL mode
        if not self.args.url:
            console.print("[red]错误: 请提供目标URL[/red]")
            sys.exit(1)

        url = self.args.url
        # Auto-prepend https:// if no scheme is provided (matching batch mode behavior)
        if url and not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        if not self._validate_url(url):
            console.print(f"[red]错误: 无效的URL格式: {self.args.url}[/red]")
            sys.exit(1)

        if self.args.deep and not self._confirm_deep_scan():
            console.print("[yellow]已取消检测[/yellow]")
            return

        result = await self._run_detection(url)

        self._output_result(result)

    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        return url.startswith(("http://", "https://"))

    def _confirm_deep_scan(self) -> bool:
        """Confirm before deep scan"""
        if not self.args.deep:
            return True

        console.print("\n[yellow]⚠️  深度检测即将开始，这将会：[/yellow]")
        console.print("  • 发送更多请求（最多50次）")
        console.print("  • 可能触发目标网站的防御机制")
        console.print("  • 可能导致IP被临时封禁\n")

        response = input("是否继续？[y/N]: ").strip().lower()
        return response in ["y", "yes"]

    def _setup_client(self):
        """Initialize HTTP client"""
        self.client = HttpClient(
            timeout=self.args.timeout,
            proxy=self.args.proxy,
            user_agent=self.args.user_agent,
            disable_cache=getattr(self.args, 'no_cache', False),
        )

    async def _run_detection(self, url: str) -> CrawlFeasibilityResult:
        """Run the detection process for a single URL"""
        self._setup_client()
        assert self.client is not None

        console.print(f"\n[cyan]🔍 正在检测 {url}...[/cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            basic_task = progress.add_task("基础信息检测...", total=None)
            basic_checker = BasicChecker(self.client)
            basic_result = await basic_checker.check(url)
            progress.update(basic_task, completed=True, description="✓ 基础信息检测完成")

            tech_task = progress.add_task("技术栈识别...", total=None)
            tech_checker = TechStackChecker(self.client)
            tech_result = await tech_checker.check(url)
            progress.update(tech_task, completed=True, description="✓ 技术栈识别完成")

            anti_task = progress.add_task("反爬特征检测...", total=None)
            anti_checker = AntiSpiderChecker(self.client, deep=self.args.deep)
            anti_result = await anti_checker.check(url)
            progress.update(anti_task, completed=True, description="✓ 反爬特征检测完成")

            assess_task = progress.add_task("综合评估...", total=None)
            assessor = Assessor()
            assessment_result = assessor.assess(basic_result, tech_result, anti_result)
            progress.update(assess_task, completed=True, description="✓ 综合评估完成")

        result = CrawlFeasibilityResult(
            url=url,
            basic=basic_result,
            tech_stack=tech_result,
            anti_spider=anti_result,
            assessment=assessment_result,
        )

        return result

    def _format_result(self, result: CrawlFeasibilityResult) -> str:
        """Format the result according to the specified format"""
        if self.args.json or self.args.format == 'json':
            return result.to_json()
        elif self.args.format == 'yaml':
            return yaml.dump(result.to_dict(), allow_unicode=True, sort_keys=False)
        elif self.args.format == 'html':
            return self._result_to_html(result)
        elif self.args.format == 'markdown':
            return self._result_to_markdown(result)
        elif self.args.format == 'pdf':
            # For PDF, we'll return the file path since PDF generation writes to a file
            # This will be handled specially in _output_result
            return self._result_to_pdf(result)
        else:
            # Fallback to JSON
            return result.to_json()

    def _result_to_html(self, result: CrawlFeasibilityResult) -> str:
        """Convert result to HTML report"""
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>CrawlFeasibility Report - {result.url}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .meta {{ color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px; }}
        .section {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
        .section:last-child {{ border-bottom: none; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
        .item {{ background: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .label {{ font-weight: bold; color: #34495e; }}
        .value {{ margin-top: 5px; }}
        .difficulty-low {{ color: #27ae60; }}
        .difficulty-medium {{ color: #f39c12; }}
        .difficulty-high {{ color: #e74c3c; }}
        .risk-list {{ list-style: none; padding: 0; }}
        .risk-list li {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 5px 0; border-radius: 3px; }}
        .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #95a5a6; font-size: 0.9em; }}
    </style>
</head>
<body>
<div class="container">
    <h1>爬虫可行性评估报告</h1>
    <div class="meta">
        目标网址: <a href="{result.url}" target="_blank">{result.url}</a><br>
        评估时间: {result.timestamp}
    </div>
    
    <div class="section">
        <h2>📊 综合评估</h2>
        <div class="grid">
            <div class="item">
                <div class="label">难度等级</div>
                <div class="value difficulty-{result.assessment.difficulty}">{result.assessment.difficulty}</div>
            </div>
            <div class="item">
                <div class="label">推荐工具</div>
                <div class="value">{result.assessment.recommended_tool}</div>
            </div>
        </div>
        {f'<div class="section"><h3>⚠️ 关键风险</h3><ul class="risk-list">{"".join([f"<li>{risk}</li>" for risk in result.assessment.key_risks])}</ul></div>' if result.assessment.key_risks else ''}
    </div>
    
    <div class="section">
        <h2>📋 基础信息</h2>
        <div class="grid">
            <div class="item">
                <div class="label">robots.txt</div>
                <div class="value">{"存在" if result.basic.robots_txt_exists else "不存在"}</div>
            </div>
            <div class="item">
                <div class="label">sitemap</div>
                <div class="value">{"存在" if result.basic.sitemap_urls else "不存在"}</div>
            </div>
            <div class="item">
                <div class="label">RSS/Atom</div>
                <div class="value">{"存在" if result.basic.rss_urls else "不存在"}</div>
            </div>
            <div class="item">
                <div class="label">API文档</div>
                <div class="value">{"存在" if result.basic.api_docs else "不存在"}</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>🔧 技术栈识别</h2>
        <div class="grid">
            <div class="item">
                <div class="label">前端框架</div>
                <div class="value">{result.tech_stack.framework}</div>
            </div>
            <div class="item">
                <div class="label">动态渲染</div>
                <div class="value">{"是" if result.tech_stack.dynamic_rendering else "否"}</div>
            </div>
            <div class="item">
                <div class="label">WAF/CDN</div>
                <div class="value">{result.tech_stack.cdn_waf}</div>
            </div>
            <div class="item">
                <div class="label">验证码</div>
                <div class="value">{', '.join(result.tech_stack.captcha) if result.tech_stack.captcha else '无'}</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>🛡️ 反爬特征检测</h2>
        <div class="grid">
            <div class="item">
                <div class="label">User-Agent检查</div>
                <div class="value">{result.anti_spider.user_agent_check}</div>
            </div>
            <div class="item">
                <div class="label">Referer检查</div>
                <div class="value">{result.anti_spider.referer_check}</div>
            </div>
            <div class="item">
                <div class="label">Cookie依赖</div>
                <div class="value">{result.anti_spider.cookie_dependency}</div>
            </div>
            <div class="item">
                <div class="label">频率限制</div>
                <div class="value">{"触发" if result.anti_spider.rate_limit_triggered else "未触发"}</div>
            </div>
            <div class="item">
                <div class="label">JS挑战</div>
                <div class="value">{"是" if result.anti_spider.js_challenge else "否"}</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>💻 代码模板建议</h2>
        <pre><code>{result.assessment.code_template}</code></pre>
    </div>
    
    <div class="section">
        <h2>📜 合规提醒</h2>
        <pre>{result.assessment.legal_note}</pre>
    </div>
    
    <div class="footer">
        © 2026 CrawlFeasibility. 本工具仅供技术调研和学习使用，请遵守相关法律法规。
    </div>
</div>
</html>
"""
        return html

    def _result_to_markdown(self, result: CrawlFeasibilityResult) -> str:
        """Convert result to Markdown report"""
        md = f"""# CrawlFeasibility 报告

**目标网址**: [{result.url}]({result.url})  
**评估时间**: {result.timestamp}

## 📊 综合评估

| 项目 | 值 |
|------|----|
| 难度等级 | {result.assessment.difficulty} |
| 推荐工具 | {result.assessment.recommended_tool} |

{"## ⚠️ 关键风险\n" + "\n".join([f"- {risk}" for risk in result.assessment.key_risks]) if result.assessment.key_risks else ""}

## 📋 基础信息

| 项目 | 值 |
|------|----|
| robots.txt | {"存在" if result.basic.robots_txt_exists else "不存在"} |
| sitemap | {"存在" if result.basic.sitemap_urls else "不存在"} |
| RSS/Atom | {"存在" if result.basic.rss_urls else "不存在"} |
| API文档 | {"存在" if result.basic.api_docs else "不存在"} |

## 🔧 技术栈识别

| 项目 | 值 |
|------|----|
| 前端框架 | {result.tech_stack.framework} |
| 动态渲染 | {"是" if result.tech_stack.dynamic_rendering else "否"} |
| WAF/CDN | {result.tech_stack.cdn_waf} |
| 验证码 | {', '.join(result.tech_stack.captcha) if result.tech_stack.captcha else '无'} |

## 🛡️ 反爬特征检测

| 项目 | 值 |
|------|----|
| User-Agent检查 | {result.anti_spider.user_agent_check} |
| Referer检查 | {result.anti_spider.referer_check} |
| Cookie依赖 | {result.anti_spider.cookie_dependency} |
| 频率限制 | {"触发" if result.anti_spider.rate_limit_triggered else "未触发"} |
| JS挑战 | {"是" if result.anti_spider.js_challenge else "否"} |

## 💻 代码模板建议

```python
{result.assessment.code_template}
```

## 📜 合规提醒

{result.assessment.legal_note}

---
*本报告由 CrawlFeasibility 生成，仅供参考。*
"""
        return md

    def _result_to_pdf(self, result: CrawlFeasibilityResult) -> str:
        """Convert result to PDF report"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
            
            # Create a temporary file path if not specified
            if self.args.output:
                output_path = Path(self.args.output)
                # Ensure the extension matches the format if not provided
                if not output_path.suffix:
                    output_path = output_path.with_suffix('.pdf')
            else:
                # Generate a default filename based on URL
                safe_name = result.url.replace("://", "_").replace("/", "_").replace("?", "_").replace("=", "_")
                output_path = Path(f"{safe_name}.pdf")
            
            # Try to register a Chinese font, fallback to DejaVu Sans if not available
            try:
                # Try to register a Unicode font that supports Chinese
                pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
                font_name = 'DejaVu'
            except:
                try:
                    # Try alternative path for DejaVu
                    pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
                    font_name = 'DejaVu'
                except:
                    # Final fallback to Helvetica (limited Unicode support)
                    font_name = 'Helvetica'
            
            # Create the PDF document
            doc = SimpleDocTemplate(str(output_path), pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Create styles with Unicode font
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=24,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            normal_style = ParagraphStyle(
                'NormalStyle',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                leading=14
            )
            heading2_style = ParagraphStyle(
                'Heading2Style',
                parent=styles['Heading2'],
                fontName=font_name,
                fontSize=14,
                spaceAfter=6,
                leading=18
            )
            code_style = ParagraphStyle(
                'CodeStyle',
                parent=styles['Code'],
                fontName=font_name,
                fontSize=9,
                leading=12
            )
            italic_style = ParagraphStyle(
                'ItalicStyle',
                parent=styles['Italic'],
                fontName=font_name,
                fontSize=9,
                leading=12
            )
            
            # Title
            story.append(Paragraph("爬虫可行性评估报告", title_style))
            story.append(Spacer(1, 12))
            
              # URL and timestamp
            story.append(Paragraph(f"<b>目标网址:</b> {result.url}", normal_style))
            story.append(Paragraph(f"<b>评估时间:</b> {result.timestamp}", normal_style))
            story.append(Spacer(1, 20))
            
              # Overall Assessment
            story.append(Paragraph("📊 综合评估", heading2_style))
            assessment_data = [
                ['难度等级', result.assessment.difficulty],
                ['推荐工具', result.assessment.recommended_tool]
            ]
            assessment_table = Table(assessment_data, colWidths=[2*inch, 4*inch])
            assessment_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(assessment_table)
            story.append(Spacer(1, 12))
            
            # Key Risks
            if result.assessment.key_risks:
                story.append(Paragraph("⚠️ 关键风险", heading2_style))
                for risk in result.assessment.key_risks:
                    story.append(Paragraph(f"• {risk}", normal_style))
                story.append(Spacer(1, 12))
            
            # Basic Information
            story.append(Paragraph("📋 基础信息", heading2_style))
            basic_data = [
                ['robots.txt', "存在" if result.basic.robots_txt_exists else "不存在"],
                ['sitemap', "存在" if result.basic.sitemap_urls else "不存在"],
                ['RSS/Atom', "存在" if result.basic.rss_urls else "不存在"],
                ['API文档', "存在" if result.basic.api_docs else "不存在"]
            ]
            basic_table = Table(basic_data, colWidths=[2*inch, 4*inch])
            basic_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(basic_table)
            story.append(Spacer(1, 12))
            
             # Technology Stack
            story.append(Paragraph("🔧 技术栈识别", heading2_style))
            tech_data = [
                ['前端框架', result.tech_stack.framework],
                ['动态渲染', "是" if result.tech_stack.dynamic_rendering else "否"],
                ['WAF/CDN', result.tech_stack.cdn_waf],
                ['验证码', ', '.join(result.tech_stack.captcha) if result.tech_stack.captcha else '无']
            ]
            tech_table = Table(tech_data, colWidths=[2*inch, 4*inch])
            tech_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(tech_table)
            story.append(Spacer(1, 12))
            
            # Anti-Spider Features
            story.append(Paragraph("🛡️ 反爬特征检测", styles['Heading2']))
            anti_data = [
                ['User-Agent检查', result.anti_spider.user_agent_check],
                ['Referer检查', result.anti_spider.referer_check],
                ['Cookie依赖', result.anti_spider.cookie_dependency],
                ['频率限制', "触发" if result.anti_spider.rate_limit_triggered else "未触发"],
                ['JS挑战', "是" if result.anti_spider.js_challenge else "否"]
            ]
            anti_table = Table(anti_data, colWidths=[2*inch, 4*inch])
            anti_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(anti_table)
            story.append(Spacer(1, 12))
            
            # Code Template
            story.append(Paragraph("💻 代码模板建议", styles['Heading2']))
            story.append(Preformatted(result.assessment.code_template, styles['Code']))
            story.append(Spacer(1, 12))
            
            # Legal Note
            story.append(Paragraph("📜 合规提醒", styles['Heading2']))
            story.append(Preformatted(result.assessment.legal_note, styles['Normal']))
            story.append(Spacer(1, 12))
            
            # Footer
            story.append(Paragraph("本报告由 CrawlFeasibility 生成，仅供参考。", styles['Italic']))
            
            # Build PDF
            doc.build(story)
            
            return str(output_path)
        except ImportError:
            # Fallback if reportlab is not available
            console.print("[yellow]警告: 未安装 reportlab 库，无法生成 PDF 报告[/yellow]")
            console.print("[yellow]请运行: pip install reportlab[/yellow]")
            # Return JSON as fallback
            return result.to_json()
        except Exception as e:
            console.print(f"[red]生成 PDF 时出错: {e}[/red]")
            # Return JSON as fallback
            return result.to_json()

    def _output_result(self, result: CrawlFeasibilityResult):
        """Output the detection result"""
        # Handle baseline comparison if specified
        if hasattr(self.args, 'baseline') and self.args.baseline:
            self._output_comparison_result(result)
            return
        
        # Special handling for PDF format
        if self.args.format == 'pdf':
            output_path = self._format_result(result)  # This now returns a file path for PDF
            if self.args.output:
                # User specified output path, move the generated file there
                import shutil
                final_path = Path(self.args.output)
                # Ensure the extension matches the format if not provided
                if not final_path.suffix:
                    final_path = final_path.with_suffix('.pdf')
                # Ensure directory exists
                final_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(output_path, str(final_path))
                console.print(f"\n[green]✓ PDF报告已保存到 {final_path}[/green]")
            else:
                # Use the generated file path directly
                console.print(f"\n[green]✓ PDF报告已保存到 {output_path}[/green]")
            return
        
        # Handle other formats
        if self.args.json or self.args.output:
            output_str = self._format_result(result)
            
            if self.args.output:
                output_path = Path(self.args.output)
                # Ensure the extension matches the format if not provided
                if not output_path.suffix:
                    ext_map = {'json': '.json', 'yaml': '.yaml', 'html': '.html', 'markdown': '.md'}
                    output_path = output_path.with_suffix(ext_map.get(self.args.format, '.json'))
                output_path.write_text(output_str, encoding="utf-8")
                console.print(f"\n[green]✓ 结果已保存到 {self.args.output}[/green]")
            else:
                print(output_str)
        else:
            self._print_pretty_result(result)

    def _output_comparison_result(self, result: CrawlFeasibilityResult):
        """Output comparison with baseline"""
        baseline_path = Path(self.args.baseline)
        if not baseline_path.exists():
            console.print(f"[red]错误: 基线文件不存在: {self.args.baseline}[/red]")
            sys.exit(1)
        try:
            baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
            baseline_result = CrawlFeasibilityResult(
                url=baseline_data["url"],
                timestamp=baseline_data["timestamp"],
                basic=BasicResult(**baseline_data["basic"]) if baseline_data.get("basic") else None,
                tech_stack=TechStackResult(**baseline_data["tech_stack"]) if baseline_data.get("tech_stack") else None,
                anti_spider=AntiSpiderResult(**baseline_data["anti_spider"]) if baseline_data.get("anti_spider") else None,
                assessment=AssessmentResult(**baseline_data["assessment"]) if baseline_data.get("assessment") else None,
            )
        except Exception as e:
            console.print(f"[red]错误: 无法读取基线文件: {e}[/red]")
            sys.exit(1)

        comparison = result.compare(baseline_result)
        console.print("\n[cyan]🔍 基线比较结果[/cyan]")
        console.print(f"基线文件: {self.args.baseline}")
        console.print(f"当前URL: {result.url}")
        console.print(f"基线URL: {baseline_result.url}")
        console.print("")

        # Helper to print a section
        def _print_section(title, diff_dict):
            if not diff_dict or (isinstance(diff_dict, dict) and diff_dict.get("missing") is True):
                return
            changed = False
            for key, change in diff_dict.items():
                if isinstance(change, dict) and "old" in change and "new" in change:
                    if change["old"] != change["new"]:
                        changed = True
                elif isinstance(change, dict) and "added" in change and "removed" in change:
                    if change["added"] or change["removed"]:
                        changed = True
            if not changed:
                return
            console.print(f"[yellow]{title}:[/yellow]")
            for key, change in diff_dict.items():
                if isinstance(change, dict) and "old" in change and "new" in change:
                    if change["old"] != change["new"]:
                        console.print(f"  {key}: {change['old']} → {change['new']}")
                elif isinstance(change, dict) and "added" in change and "removed" in change:
                    added = change["added"]
                    removed = change["removed"]
                    if added:
                        console.print(f"  {key} 新增: {', '.join(added)}")
                    if removed:
                        console.print(f"  {key} 移除: {', '.join(removed)}")
                # Ignore other structures for simplicity

        _print_section("基础信息", comparison.get("basic", {}))
        _print_section("技术栈", comparison.get("tech_stack", {}))
        _print_section("反爬特征", comparison.get("anti_spider", {}))
        _print_section("综合评估", comparison.get("assessment", {}))

        # Also show if URL or timestamp changed (though URL should be same for comparison)
        if comparison.get("url_changed"):
            console.print(f"[yellow]URL变化:[/yellow]  {baseline_result.url} → {result.url}")
        if comparison.get("timestamp_changed"):
            console.print(f"[yellow]时间戳变化:[/yellow]  {baseline_result.timestamp} → {result.timestamp}")

        console.print("")

    def _print_pretty_result(self, result: CrawlFeasibilityResult):
        """Print result in pretty format"""
        console.print("\n" + "=" * 50)

        table = Table(title="📊 综合评估", show_header=False)
        table.add_column(style="cyan")
        table.add_column()

        table.add_row("URL", result.url)
        table.add_row("难度", f"[{'red' if result.assessment.difficulty == 'high' else 'yellow' if result.assessment.difficulty == 'medium' else 'green'}]{result.assessment.difficulty}[/]")
        table.add_row("推荐工具", result.assessment.recommended_tool)

        console.print(table)

        if result.assessment.key_risks:
            console.print("\n[yellow]⚠️  关键风险:[/yellow]")
            for risk in result.assessment.key_risks:
                console.print(f"  • {risk}")

        console.print("\n[green]基础信息:[/green]")
        console.print(f"  • robots.txt: {'存在' if result.basic.robots_txt_exists else '不存在'}")
        console.print(f"  • sitemap: {'存在' if result.basic.sitemap_urls else '不存在'}")
        console.print(f"  • RSS: {'存在' if result.basic.rss_urls else '不存在'}")
        console.print(f"  • API文档: {'存在' if result.basic.api_docs else '不存在'}")

        console.print("\n[blue]技术栈:[/blue]")
        console.print(f"  • 框架: {result.tech_stack.framework}")
        console.print(f"  • 动态渲染: {'是' if result.tech_stack.dynamic_rendering else '否'}")
        console.print(f"  • WAF/CDN: {result.tech_stack.cdn_waf}")
        console.print(f"  • 验证码: {', '.join(result.tech_stack.captcha) if result.tech_stack.captcha else '无'}")

        console.print("\n[red]反爬特征:[/red]")
        console.print(f"  • User-Agent检查: {result.anti_spider.user_agent_check}")
        console.print(f"  • Referer检查: {result.anti_spider.referer_check}")
        console.print(f"  • Cookie依赖: {result.anti_spider.cookie_dependency}")
        console.print(f"  • 频率限制: {'触发' if result.anti_spider.rate_limit_triggered else '未触发'}")
        console.print(f"  • JS挑战: {'是' if result.anti_spider.js_challenge else '否'}")

        console.print("\n" + "=" * 50)

    async def _run_batch(self):
        """Run batch detection from a file"""
        batch_file = Path(self.args.batch)
        if not batch_file.exists():
            console.print(f"[red]错误: 批量文件不存在: {self.args.batch}[/red]")
            sys.exit(1)

        # Read URLs from file
        urls = []
        with open(batch_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Prepend http:// if no scheme
                if not line.startswith(('http://', 'https://')):
                    line = 'https://' + line
                urls.append(line)

        if not urls:
            console.print("[red]错误: 没有有效的URL在批量文件中[/red]")
            sys.exit(1)

        console.print(f"[cyan]🔍 开始批量检测: {len(urls)} 个URL[/cyan]\n")

        # Setup client once for batch
        self._setup_client()

        results = []
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
             console=console,
         ) as progress:
             batch_task = progress.add_task("批量检测中...", total=len(urls))
 
             for i, url in enumerate(urls):
                 progress.update(batch_task, description=f"[{i+1}/{len(urls)}] 正在检测 {url}")
                 try:
                     result = await self._run_detection_for_batch(url)
                     results.append(result)
 
                     # Output individual result if not merging
                     if not self.args.merge:
                         if self.args.output_dir:
                             output_dir = Path(self.args.output_dir)
                             output_dir.mkdir(parents=True, exist_ok=True)
                             # Create a safe filename from the URL
                             safe_name = url.replace("://", "_").replace("/", "_").replace("?", "_").replace("=", "_")
                             
                             # Special handling for PDF format
                             if self.args.format == 'pdf':
                                 # Generate PDF and get the file path
                                 pdf_path = self._format_result(result)  # Returns file path for PDF
                                 # Move to output directory with proper name
                                 output_filename = f"{safe_name}.pdf"
                                 output_path = output_dir / output_filename
                                 import shutil
                                 shutil.move(pdf_path, str(output_path))
                                 console.print(f"[dim]  PDF报告已保存到 {output_path}[/dim]")
                             else:
                                 # Handle other formats
                                 ext_map = {'json': '.json', 'yaml': '.yaml', 'html': '.html', 'markdown': '.md'}
                                 ext = ext_map.get(self.args.format, '.json')
                                 output_path = output_dir / f"{safe_name}{ext}"
                                 output_path.write_text(self._format_result(result), encoding="utf-8")
                         elif self.args.output:
                             # If --output is given, use it as a base name and append index
                             base_path = Path(self.args.output)
                             
                             # Special handling for PDF format
                             if self.args.format == 'pdf':
                                 # Generate PDF and get the file path
                                 pdf_path = self._format_result(result)  # Returns file path for PDF
                                 # Ensure the extension matches the format if not provided
                                 if not base_path.suffix:
                                     base_path = base_path.with_suffix('.pdf')
                                 # Create indexed filename
                                 output_path = base_path.parent / f"{base_path.stem}_{i}{base_path.suffix}"
                                 # Ensure directory exists
                                 output_path.parent.mkdir(parents=True, exist_ok=True)
                                 import shutil
                                 shutil.move(pdf_path, str(output_path))
                                 console.print(f"[dim]  PDF报告已保存到 {output_path}[/dim]")
                             else:
                                 # Handle other formats
                                 if not base_path.suffix:
                                     ext_map = {'json': '.json', 'yaml': '.yaml', 'html': '.html', 'markdown': '.md'}
                                     ext = ext_map.get(self.args.format, '.json')
                                     base_path = base_path.with_suffix(ext)
                                 output_path = base_path.parent / f"{base_path.stem}_{i}{base_path.suffix}"
                                 output_path.write_text(self._format_result(result), encoding="utf-8")
                         else:
                             # No output specified, do nothing (to avoid console flood)
                             pass
                 except Exception as e:
                     logger.error(f"Failed to process {url}: {e}")
                     failed += 1
                 finally:
                     progress.advance(batch_task)

        # After processing all URLs
        console.print(f"\n[green]✓ 批量检测完成: 成功 {len(results)}, 失败 {failed}[/green]")

        if self.args.merge:
            merge_file = Path(self.args.merge)
            # Write all results as a JSON array (merge is always JSON for now)
            merge_data = [result.to_dict() for result in results]
            merge_file.write_text(json.dumps(merge_data, indent=2, ensure_ascii=False), encoding="utf-8")
            console.print(f"[green]✓ 合并结果已保存到 {self.args.merge}[/green]")

        # If we have output_dir and not merging, we already saved individual files.
        # If we have --output and not merging and not --output-dir, we saved indexed files.

    async def _run_detection_for_batch(self, url: str) -> CrawlFeasibilityResult:
        """Run detection for a single URL in batch mode (without console output)"""
        # We reuse the same logic as _run_detection but without the progress display and console prints.
        # We'll create a new progress-less version.

        # Create checkers
        basic_checker = BasicChecker(self.client)
        tech_checker = TechStackChecker(self.client)
        anti_checker = AntiSpiderChecker(self.client, deep=self.args.deep)
        assessor = Assessor()

        # Run checks
        basic_result = await basic_checker.check(url)
        tech_result = await tech_checker.check(url)
        anti_result = await anti_checker.check(url)
        assessment_result = assessor.assess(basic_result, tech_result, anti_result)

        # Build result
        result = CrawlFeasibilityResult(
            url=url,
            basic=basic_result,
            tech_stack=tech_result,
            anti_spider=anti_result,
            assessment=assessment_result,
        )

        return result


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        prog="crawlfeasibility",
        description="爬虫可行性评估工具 - 快速了解目标网站的抓取难度",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("url", nargs="?", help="目标网址")
    parser.add_argument(
        "-b", "--batch", type=str, help="批量检测文件（每行一个URL）"
    )
    parser.add_argument(
        "-d", "--deep", action="store_true", help="深度检测（更多请求）"
    )
    parser.add_argument(
        "-o", "--output", type=str, help="输出到文件（单URL模式）或批量模式下的基础文件名"
    )
    parser.add_argument(
        "--output-dir", type=str, help="批量输出目录（批量模式）"
    )
    parser.add_argument(
        "--merge", type=str, help="合并批量结果到一个JSON文件（批量模式）"
    )
    parser.add_argument(
        "-j", "--json", action="store_true", help="JSON输出模式"
    )
    parser.add_argument(
        "--format", choices=["json", "yaml", "html", "markdown", "pdf"], default="json", help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "-t", "--timeout", type=int, default=10, help="请求超时秒数 (默认: 10)"
    )
    parser.add_argument(
        "-u", "--user-agent", type=str, help="自定义User-Agent"
    )
    parser.add_argument(
        "-p", "--proxy", type=str, help="代理地址"
    )
    parser.add_argument(
        "-v", "--verbose", action=argparse.BooleanOptionalAction, help="详细输出"
    )
    parser.add_argument(
        "--version", action="store_true", help="显示版本"
    )
    parser.add_argument(
        "--check-env", action="store_true", help="检查环境配置"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="禁用缓存，强制重新检测"
    )
    parser.add_argument(
        "--clear-cache", action="store_true", help="清除所有缓存"
    )
    parser.add_argument(
        "--baseline", type=str, help="Path to a baseline result file (JSON) for comparison"
    )

    return parser


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()

    # Handle --clear-cache flag
    if hasattr(args, 'clear_cache') and args.clear_cache:
        cache_manager.clear()
        console.print("[green]✓ 缓存已清除[/green]")
        return

    # Setup logging
    config.setup_logging(args.verbose if hasattr(args, 'verbose') else False)

    if hasattr(args, 'check_env') and args.check_env:
        print(f"CrawlFeasibility v{__version__}")
        print("-" * 40)
        config.check_environment()
        return

    # Set url to None if not provided (for batch mode)
    if not hasattr(args, 'url'):
        args.url = None

    try:
        cli = CrawlFeasibilityCLI(args)
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 检测已取消[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]❌ 错误: {e}[/red]")
        if args.verbose if hasattr(args, 'verbose') else False:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()