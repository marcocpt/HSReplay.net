import {MetricsBackend, Point} from "./MetricsBackend";


export default class InfluxMetricsBackend implements MetricsBackend {
	public async: boolean = true;

	constructor(public url: string) {
	}

	public writePoints(points: Point[]) {
		if (!points.length) {
			return;
		}
		let url = this.url;
		let blob = new Blob([
			points.map(function (point) {
				let tags = [];
				for (let tagKey in point.tags) {
					tags.push(tagKey + "=" + point.tags[tagKey]);
				}
				let values = [];
				for (let valueKey in point.values) {
					values.push(valueKey + "=" + point.values[valueKey]);
				}
				let line = point.series + (tags.length ? "," + tags.join(",") : "") + " " + values.join(",");
				return line;
			}).join("\n")], {type: "text/plain"}
		);
		let success = false;
		if (navigator["sendBeacon"]) {
			// try beacon api
			success = (navigator as any).sendBeacon(url, blob);
		}
		if (!success) {
			// fallback to plain old XML http requests
			let request = new XMLHttpRequest();
			request.open("POST", url, this.async);
			request.send(blob);
		}
	}

	public writePoint(series: string, values: Object, tags?: Object) {
		this.writePoints([{series: series, values: values, tags: tags}]);
	}

}
