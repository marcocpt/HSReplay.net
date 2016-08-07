import {StorageBackend} from "./StorageBackend";


export default class MetaDataManager {

	protected sourceUrl: (build: number|"latest", locale: string) => string;
	protected backend: StorageBackend;
	public locale: string = "enUS";

	constructor(sourceUrl: (build: number|"latest", locale: string) => string, backend: StorageBackend, locale?: string) {
		this.sourceUrl = sourceUrl;
		this.backend = backend;
		if (locale) {
			this.locale = locale;
		}
	}

	protected generateKey(build: number|"latest"): string {
		if (build === "latest") {
			throw new Error('Will not generate key for "latest" metadata');
		}
		return "hsjson_build-" + build + "_" + this.locale;
	}

	protected fetch(build: number|"latest", cb?: (data: any[]) => void, error?: () => void): void {
		let url = this.sourceUrl(build, this.locale);
		$.ajax(url, {
			type: "GET",
			dataType: "text",
			success: (data: any, textStatus: string, jqXHR: any) => {
				let result = JSON.parse(data);
				cb(result);
			},
			error: (jqXHR: any, textStatus: string, errorThrown: string) => {
				if (!jqXHR.status) {
					// request was probably cancelled
					return;
				}
				error();
			}
		});
	}

	protected has(build: number|"latest"): boolean {
		if (build === "latest") {
			return false;
		}
		return this.backend.has(this.generateKey(build));
	}

	public get(build: number|"latest", cb: (data: any[]) => void): void {
		if (!build) {
			build = "latest";
		}
		if (build !== "latest") {
			let key = this.generateKey(build);
			if (this.backend.has(key)) {
				cb(this.backend.get(key));
				return;
			}
		}
		this.fetch(build, (data: any[]) => {
			cb(data);
			if (build !== "latest") {
				this.backend.set(this.generateKey(build), data);
			}
		}, () => {
			// fallback to latest
			this.get("latest", cb);
		});
	}
}
