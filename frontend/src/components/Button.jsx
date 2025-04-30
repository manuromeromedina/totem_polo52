const Button = ({ children, onClick, type = "button" }) => (
    <button type={type} onClick={onClick} className="btn">
      {children}
    </button>
  )
  
  export default Button
  