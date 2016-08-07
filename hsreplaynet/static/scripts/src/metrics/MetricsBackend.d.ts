export interface Point {
	series: string;
	values: Object;
	tags?: Object;
}

export interface MetricsBackend {
	writePoint(series: string, values: Object, tags?: Object);
	writePoints(points: Point[]);
}
