# OWL本体类层级导出工具

这个工具可以将OWL本体文件中的所有类按照层级结构导出为JSON和Markdown格式。

## 功能特性

- ✅ 递归遍历整个类层级结构
- ✅ 导出为JSON格式（嵌套结构，包含完整 IRI 信息）
- ✅ 导出为Markdown格式（无序列表带缩进，简洁易读，不含 IRI）
- ✅ 支持类的标签（label）和注释（comment）
- ✅ 避免循环引用问题
- ✅ 可选导出扁平列表（包含父类信息和 IRI）
- ✅ 自定义根类和输出路径
- ✅ 支持中文等多语言字符

## 安装依赖

```bash
pip install owlready2
```

或使用 conda 环境：

```bash
conda run -n OntologyConstruction python export_ontology_hierarchy.py <参数>
```

## 使用方法

### 基本用法

```bash
python export_ontology_hierarchy.py <本体文件路径>
```

这将生成两个文件：
- `ontology_hierarchy.json` - JSON格式的层级结构
- `ontology_hierarchy.md` - Markdown格式的层级结构（无序列表带缩进）

### 指定输出路径

```bash
python export_ontology_hierarchy.py ontology.owl --output results/my_ontology
```

这将生成：
- `results/my_ontology.json`
- `results/my_ontology.md`

### 同时导出扁平列表

```bash
python export_ontology_hierarchy.py ontology.owl --flat
```

这将额外生成：
- `ontology_hierarchy_flat.json` - 所有类的扁平列表（包含父类信息）

### 指定根类

```bash
python export_ontology_hierarchy.py ontology.owl --root MyRootClass
```

从指定的类开始构建层级（而不是默认的 Thing）

### 实际示例

```bash
# 导出 2.5 max 本体
conda run -n OntologyConstruction python export_ontology_hierarchy.py \
    "../../data/ontology/2.5 max back up.owl" \
    --output 2.5_max \
    --flat

# 导出 3 max 本体
conda run -n OntologyConstruction python export_ontology_hierarchy.py \
    "../../data/ontology/3 max.owl" \
    --output 3_max \
    --flat
```

## 输出格式示例

### 导出成功示例

```bash
正在加载本体文件: src/external/MOSES/data/ontology/3 max.owl
✓ 本体加载成功
正在构建类层级结构（从 Thing 开始）...
✓ 层级结构构建完成，共 217 个类
✓ JSON格式已导出到: src/external/MOSES/test/onto_export/3_max.json
✓ Markdown格式已导出到: src/external/MOSES/test/onto_export/3_max.md
✓ 扁平列表已导出到: src/external/MOSES/test/onto_export/3_max_flat.json

✓ 所有导出完成!
  - 类层级总数: 217
  - 本体中定义的类总数: 206
```

### JSON格式

```json
{
  "name": "Thing",
  "iri": "http://www.w3.org/2002/07/owl#Thing",
  "children": [
    {
      "name": "Person",
      "iri": "http://example.org/ontology#Person",
      "label": "人",
      "comment": "表示一个人的类",
      "children": [
        {
          "name": "Student",
          "iri": "http://example.org/ontology#Student",
          "label": "学生",
          "children": []
        },
        {
          "name": "Teacher",
          "iri": "http://example.org/ontology#Teacher",
          "label": "教师",
          "children": []
        }
      ]
    }
  ]
}
```

### Markdown格式

```markdown
# Ontology Class Hierarchy

Total classes: 4

---

- **Thing**
  - **人 (Person)**
    - Comment: 表示一个人的类
    - **学生 (Student)**
    - **教师 (Teacher)**
```

**注意**: Markdown 格式为了简洁，不显示 IRI 信息。如需 IRI，请查看 JSON 或扁平列表文件。

### 扁平列表格式（使用 --flat）

```json
[
  {
    "name": "Person",
    "iri": "http://example.org/ontology#Person",
    "label": "人",
    "direct_parents": ["Thing"]
  },
  {
    "name": "Student",
    "iri": "http://example.org/ontology#Student",
    "label": "学生",
    "direct_parents": ["Person"]
  },
  {
    "name": "Teacher",
    "iri": "http://example.org/ontology#Teacher",
    "label": "教师",
    "direct_parents": ["Person"]
  }
]
```

## 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `ontology_file` | - | OWL本体文件路径（必需） | - |
| `--output` | `-o` | 输出文件前缀 | `ontology_hierarchy` |
| `--flat` | - | 同时导出扁平列表 | False |
| `--root` | - | 指定根类名称 | `Thing` |

## 常见问题

### 1. 循环引用怎么处理？

脚本会自动检测并标记循环引用，在输出中添加 `"note": "circular_reference"` 标记。

### 2. 支持哪些本体文件格式？

支持所有 owlready2 能够加载的格式：
- `.owl` (RDF/XML)
- `.rdf`
- `.ttl` (Turtle)
- `.n3`

### 3. 如何处理多个根类？

如果您的本体有多个顶层类（不直接继承自Thing），脚本默认会从Thing开始遍历所有类。您也可以使用 `--root` 参数指定特定的根类。

### 4. 性能如何？

脚本使用递归遍历，对于大型本体（数千个类）也能正常工作。如果遇到性能问题，可以考虑使用 `--root` 参数限制遍历范围。

## 技术细节

- 使用 `owlready2` 库加载和解析本体
- 递归遍历类的 `.subclasses()` 方法
- 自动提取类的 `label` 和 `comment` 属性
- 使用集合追踪已访问节点避免无限循环
- UTF-8编码支持中文等多语言字符

## 许可证

MIT License
