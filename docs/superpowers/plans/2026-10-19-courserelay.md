# CourseRelay Implementation Plan

执行方式：当前会话自主逐项执行，使用writing-plans、test-driven-development和verification-before-completion。新建独立仓库，开发分支work/personal-course-desk；不修改其他源码项目。

目标：用户能在中文界面持续发现课程资料遗漏及稿件过期，并导出可执行的人工补资料交接单。

架构：标准库Python、SQLite及本地HTTP。读取课程原件，私人状态在源码目录外。PDF无法提取时保留UNKNOWN。

- [x] 文件边界与正文提取。文件courserelay/formats.py、courserelay/safe_files.py、tests/test_formats.py。先以真实临时DOCX测试段落提取、DTD拒绝和膨胀限制，再实现extract(path, roots)返回text和format_note；复用固定上游文件读取边界，不添加网络下载。
- [x] 扫描及覆盖关系。文件courserelay/store.py、tests/test_store.py。先测试源变化使覆盖失效、输出改变使当前版失效、重复扫描保持快照、受限扫描不标删除。接口Store.add_course(title, root)、scan(id)、dashboard(id)、cover(source, output, coverage, scope)、choose(file, kind)。SQLite关系绑定具体sha，返回可解释状态。
- [x] 配套核验与交接。文件courserelay/bundles.py、courserelay/handoff.py、tests/test_bundle.py。测试两匹配一不同、缺文件、穿越和重复成员。audit(store, archive_id, directory)只返回诊断；handoff(store, course_id)返回Markdown，对来源文本做字面量隔离。
- [x] CLI与中文界面。文件courserelay/__main__.py、courserelay/server.py、courserelay/web/*、tests/test_http_cli.py。先测未授权、外部Origin、非法ID、Unicode及CLI实际退出，再实现127.0.0.1界面。UI显示课程、差异、来源关联、三个用途版本、ZIP核验及交接下载。
- [x] 实际验收和交付。干净目录零安装依赖运行unittest与CLI；个人课程目录只读扫描并保存结果；浏览器真实操作；独立代码审查；记录未执行平台与提取限制。源码和私人配置分开；本地提交、源码ZIP和Bundle均不包含课程数据。

验收命令：python -X utf8 -m unittest discover -s tests -v。每项在开发前先运行对应失败测试，原始输出保存在独立验证目录。完成后提供一键启动入口、README和RESUME，停止无关扩展。
