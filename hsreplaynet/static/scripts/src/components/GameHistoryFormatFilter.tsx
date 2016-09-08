import * as React from "react";

interface GameHistoryFormatFilterProps extends React.ClassAttributes<GameHistoryFormatFilterState > {
	setQuery: (type: string) => void;
	selected: string;
}

interface GameHistoryFormatFilterState {
}

export default class GameHistoryFormatFilter extends React.Component<GameHistoryFormatFilterProps, GameHistoryFormatFilterState> {

	render(): JSX.Element {
		if (!this.props.selected) {
			this.props.selected = "";
		}
		return (
			<div>
				<select className="form-control" onChange={(e: any) => this.props.setQuery(e.target.value)} value={this.props.selected}>
					<option value="">All Formats</option>
					<option value="standard">Standard</option>
					<option value="wild">Wild</option>
				</select>
			</div>
		);
	}
}
