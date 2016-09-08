export function parseQuery(query: string): Map<string, string> {
	if (!query) {
		return new Map<string, string>();
	}
	var map: Map<string, string> = new Map<string, string>();
	query.split("&").forEach(v => {
		var kvp = v.split("=");
		if(kvp.length === 2 && kvp[0] && kvp[1]) {
			map = map.set(kvp[0], kvp[1]);
		}
	});
	return map;
}

export function toQueryString(map: Map<string, string>): string {
	if (map.size == 0) {
		return "";
	}
	var terms = [];
	map.forEach((v, k) =>{
		if (k && v) {
			terms[terms.length] = k + "=" + v
		}
	});
	return terms.join("&");
}
