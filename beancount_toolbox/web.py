import sys, io, datetime, logging
from bottle import response, request
from beancount.utils import date_utils
from beancount.ops import summarize
from beancount.utils import misc_utils
from beancount.web import web, views


class _QuarterView(views.View):
    """A view of the entries for a single month."""

    def __init__(self, entries, options_map, year, quarter):
        """Create a view clamped to one quarter.

        Args:
          entries: A list of directives.
          options_map: A dict of options, as produced by the parser.
          title: A string, the title of this view.
          year: An integer, the year of period.
          quarter: An integer, the quarter to be used as year end.
        """
        self.year = year
        self.quarter = quarter
        self.start_date = datetime.date(year, quarter * 3 - 2, 1)
        self.end_date = date_utils.next_month(
            datetime.date(year, quarter * 3, 1))

        title = f'{self.start_date:%Y}-Q{quarter}'

        views.View.__init__(self, entries, options_map, title)

        self.monthly = views.MonthNavigation.COMPACT

    def apply_filter(self, entries, options_map):
        # Clamp to the desired period.
        with misc_utils.log_time('clamp', logging.info):
            entries, index = summarize.clamp_opt(entries, self.start_date,
                                                 self.end_date, options_map)
        return entries, index, self.end_date


@web.app.route(
    r'/x/view/year/<year:re:\d\d\d\d>/quarter/<quarter:re:\d>/<path:re:.*>',
    name='quarter')
@web.handle_view(6)
def _quarter(year=None, quarter=None, path=None):
    year = int(year)
    quarter = int(quarter)

    return _QuarterView(web.app.entries, web.app.options, year, quarter)


APP_NAVIGATION_QUARTER_FULL = web.bottle.SimpleTemplate("""
<ul>
  <li><a href="{{annual}}">Annual</a></li>
  [
      <li><a href="{{q1}}">Q1</a></li>
      <li><a href="{{q2}}">Q2</a></li>
      <li><a href="{{q3}}">Q3</a></li>
      <li><a href="{{q4}}">Q4</a></li>
  ]
</ul>
""")


def _patched_render_view(*args, **kw):
    """Render the title and contents in our standard template for a view page.

    Args:
      *args: A tuple of values for the HTML template.
      *kw: A dict of optional values for the HTML template.
    Returns:
      An HTML string of the rendered template.
    """
    response.content_type = 'text/html'
    kw['A'] = web.A  # Application mapper
    kw['V'] = web.V  # View mapper
    kw['title'] = web.app.options['title']
    kw['view_title'] = ' - ' + request.view.title

    overlays = []
    if request.params.pop('render_overlay', False):
        overlays.append('<li><a href="{}">Errors</a></li>'.format(
            web.app.router.build('errors')))

    # Render navigation, with monthly navigation option.
    oss = io.StringIO()
    oss.write(
        web.APP_NAVIGATION.render(A=web.A,
                                  V=web.V,
                                  view_title=request.view.title))
    if hasattr(request.view, 'year'):
        overlays.append('<li><a href="{}">Quarterly</a></li>'.format(
            web.app.router.build('quarter',
                                 year=request.view.year,
                                 quarter=1,
                                 path=request.path[1:])))

    if request.view.monthly is views.MonthNavigation.COMPACT:
        overlays.append('<li><a href="{}">Monthly</a></li>'.format(web.M.Jan))
    elif request.view.monthly is views.MonthNavigation.FULL:
        annual = web.app.router.build('year',
                                      path=web.DEFAULT_VIEW_REDIRECT,
                                      year=request.view.year)
        oss.write(
            web.APP_NAVIGATION_MONTHLY_FULL.render(M=web.M,
                                                   Mp=web.Mp,
                                                   Mn=web.Mn,
                                                   V=web.V,
                                                   annual=annual))

    if hasattr(request.view, 'year') and hasattr(request.view, 'quarter'):
        annual = web.app.router.build('year',
                                      path=web.DEFAULT_VIEW_REDIRECT,
                                      year=request.view.year)
        oss.write(
            APP_NAVIGATION_QUARTER_FULL.render(
                annual=annual,
                **dict([(f'q{i}',
                         web.app.router.build('quarter',
                                              year=request.view.year,
                                              quarter=i,
                                              path=request.path[1:]))
                        for i in range(1, 5)])))

    kw['navigation'] = oss.getvalue()
    kw['overlay'] = web.render_overlay(' '.join(overlays))

    kw['scripts'] = kw.get('scripts', '')

    return web.template.render(*args, **kw)


web.render_view = _patched_render_view

main = web.main
