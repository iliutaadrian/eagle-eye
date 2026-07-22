"""PyInstaller / launchd entry point: start the Eagle Eye menu-bar tracker."""

from eagleeye import config, app

if __name__ == "__main__":
    cfg = config.load()
    cfg.ensure_dirs()
    app.run(cfg)
