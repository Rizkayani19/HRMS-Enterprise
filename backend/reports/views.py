from django.http import Http404, HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from .registry import REPORTS, REPORTS_BY_KEY
from .renderers import to_csv, to_pdf, to_xlsx

FORMATS = {
    "pdf": (to_pdf, "application/pdf"),
    "xlsx": (to_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "csv": (to_csv, "text/csv"),
}


class ReportListView(APIView):
    def get(self, request):
        return Response([{"key": r.key, "title": r.title, "description": r.description, "params": r.params}
                         for r in REPORTS])


class ReportView(APIView):
    def get(self, request, key, fmt="json"):
        report = REPORTS_BY_KEY.get(key)
        if not report:
            raise Http404
        result = report.build(request.query_params)
        if fmt == "json":
            return Response({"title": result.title, "subtitle": result.subtitle,
                             "columns": result.columns, "rows": result.rows})
        if fmt not in FORMATS:
            raise Http404
        render, ctype = FORMATS[fmt]
        resp = HttpResponse(render(result), content_type=ctype)
        resp["Content-Disposition"] = f'attachment; filename="{key}.{fmt}"'
        return resp
