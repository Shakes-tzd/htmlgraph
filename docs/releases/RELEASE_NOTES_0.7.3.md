# Release Notes - HtmlGraph 0.7.3

**Release Date:** December 23, 2025
**Type:** Patch Release (Infrastructure)

---

## 🔧 Infrastructure

### PyPI Trusted Publishing Enabled

- **Added**: PyPI trusted publishing configuration
- **Impact**: Automated releases via GitHub Actions now work without manual API token management
- **Benefit**: More secure and streamlined release process

---

## 📦 Installation

### PyPI (Python Package)
```bash
pip install --upgrade htmlgraph==0.7.3
```

### Claude Plugin
```bash
claude plugin update htmlgraph
```

### Verify Installation
```bash
python -c "import htmlgraph; print(htmlgraph.__version__)"
# Should output: 0.7.3
```

---

## 🔄 Upgrading from 0.7.2

**No code changes.** This is purely an infrastructure release to test trusted publishing.

---

## 🔗 Related Links

- **GitHub Release:** https://github.com/Shakes-tzd/htmlgraph/releases/tag/v0.7.3
- **PyPI Package:** https://pypi.org/project/htmlgraph/0.7.3/
- **Documentation:** https://shakes-tzd.github.io/htmlgraph/

---

**Thank you for using HtmlGraph!** 🎉
