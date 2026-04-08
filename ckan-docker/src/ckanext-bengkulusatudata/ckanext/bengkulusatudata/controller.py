import ckan.lib.base as base

render = base.render

class ArnoldController(base.BaseController):

    def index(self):
        return render("bengkulusatudata/arnold.html")