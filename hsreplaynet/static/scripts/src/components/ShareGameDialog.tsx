import * as React from "react";
import Clipboard from "clipboard";


interface ShareGameDialogProps extends React.ClassAttributes<ShareGameDialog> {
	url: string;
	turn: number;
	reveal?: boolean;
	swap?: boolean;
	alwaysLinkToTurn?: boolean;
	showLinkToTurn?: boolean;
	alwaysPreservePerspective?: boolean;
	showPreservePerspective?: boolean;
	onShare?: (network: string, linkToTurn?: boolean) => void;
}

interface ShareGameDialogState {
	linkToTurn?: boolean;
	preservePerspective?: boolean;
	confirming?: boolean;
}

export default class ShareGameDialog extends React.Component<ShareGameDialogProps, ShareGameDialogState> {

	private clipboard: Clipboard;
	private input: HTMLInputElement;
	private timeout: number = null;

	constructor(props: ShareGameDialogProps, context: any) {
		super(props, context);
		this.state = {
			linkToTurn: false,
			preservePerspective: false,
			confirming: false,
		};
	}

	componentDidMount(): void {
		this.clipboard = new Clipboard("#replay-share-copy-url", {
			text: (elem): string => this.buildUrl()
		});
		this.clipboard.on("success", () => {
			this.setState({confirming: true});
			window.clearTimeout(this.timeout);
			this.timeout = window.setTimeout(() => {
				this.setState({confirming: false});
				this.timeout = null;
			}, 1000);
			if(this.props.onShare) {
				this.props.onShare("copy", this.state.linkToTurn);
			}
		});
	}

	componentWillUnmount(): void {
		this.clipboard.destroy();
		window.clearTimeout(this.timeout);
	}

	protected buildUrl(): string {
		let url = this.props.url;
		let parts = [];
		if (this.props.turn && ((this.props.showLinkToTurn && this.state.linkToTurn) || this.props.alwaysLinkToTurn)) {
			parts.push("turn=" + Math.ceil(this.props.turn / 2) + (this.props.turn % 2 ? "a" : "b"));
		}
		if ((this.props.showPreservePerspective && this.state.preservePerspective) || this.props.alwaysPreservePerspective) {
			if(typeof this.props.reveal == "boolean" || this.props.reveal) {
				parts.push("reveal=" + (this.props.reveal ? 1 : 0));
			}
			if(typeof this.props.swap == "boolean" || this.props.swap) {
				parts.push("swap=" + (this.props.swap ? 1 : 0));
			}
		}
		if (parts.length) {
			url += "#" + parts.join("&");
		}
		return url;
	}

	protected onChangeLinkToTurn(): void {
		this.setState({linkToTurn: !this.state.linkToTurn});
	}

	protected onChangePreservePerspective(): void {
		this.setState({preservePerspective: !this.state.preservePerspective});
	}

	protected onExternalShare(e: React.MouseEvent): void {
		e.preventDefault();
		let target = e.currentTarget as HTMLElement;
		window.open(target.getAttribute("href"), "_blank", "resizable,scrollbars=yes,status=1");
		if(this.props.onShare) {
			this.props.onShare(target.getAttribute("data-network") || "unknown", this.state.linkToTurn);
		}
	}

	render(): JSX.Element {
		let url = this.buildUrl();
		return <form>
			<fieldset>
				<div className="form-group">
					<div className="input-group">
						<input type="text" readonly id="replay-share-url" className="form-control"
							   value={url}
							   onSelect={(e) => this.input.setSelectionRange(0, this.input.value.length)}
							   ref={(node) => this.input = node}/>
						<span className="input-group-btn">
							 <button className="btn btn-default" id="replay-share-copy-url"
									 type="button">{this.state.confirming ? "Copied!" : "Copy"}</button>
						</span>
					</div>
				</div>
				<a href={"https://www.reddit.com/submit?url=" + encodeURIComponent(url)} data-network="reddit" className="btn btn-default btn-xs" onClick={(e) => this.onExternalShare(e) }>Reddit</a> &nbsp;
				<a href={"https://twitter.com/intent/tweet?url=" + encodeURIComponent(url)} data-network="twitter"  className="btn btn-default btn-xs" onClick={(e) => this.onExternalShare(e) }>Twitter</a> &nbsp;
				<a href={"https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(url)} data-network="facebook" className="btn btn-default btn-xs" onClick={(e) => this.onExternalShare(e) }>Facebook</a>
			</fieldset>
			<fieldset>
				{this.props.showLinkToTurn ? <div className="checkbox">
					<label>
						<input type="checkbox" id="replay-share-link-turn" checked={this.state.linkToTurn}
							onChange={(e) => this.onChangeLinkToTurn()}/>
							Link to current turn
					</label>
				</div> : null}
				{this.props.showPreservePerspective ? <div className="checkbox">
					<label>
						<input type="checkbox" id="replay-share-link-turn" checked={this.state.preservePerspective}
							   onChange={(e) => this.onChangePreservePerspective()}/> Preserve perspective
					</label>
				</div> : null}
			</fieldset>
		</form>;
	}
}
